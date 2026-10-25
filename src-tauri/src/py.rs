//! The Python engines (numpy, SciPy, matplotlib): two worker processes, one drawing graphs and
//! one calculating results, started at launch and kept running. Requests and answers are single JSON lines (see py/worker.py). The installed app
//! uses the runtime pack (runtime.rs); a development build uses DATUM_PYTHON or the Python on
//! the PATH. A request that takes too long kills and restarts the worker.
use serde_json::Value;
use std::io::{BufRead, BufReader, Write};
use std::path::PathBuf;
use std::process::{Child, ChildStdin, Command, Stdio};
use std::sync::{mpsc, Mutex};
use std::time::Duration;
use tauri::{AppHandle, Manager};

/// How long a request may take (start-up may scan the fonts once).
const START: Duration = Duration::from_secs(180);
const REQUEST: Duration = Duration::from_secs(60);

pub struct Worker {
    child: Child,
    stdin: ChildStdin,
    /// Lines from the worker's stdout, read by a thread so waiting can time out.
    lines: mpsc::Receiver<String>,
}

#[derive(Default)]
pub struct Py {
    worker: Option<Worker>,
    /// Python, numpy, scipy and matplotlib versions once the engine has answered.
    pub versions: Option<Value>,
    pub error: Option<String>,
    /// The last few renders, so unchanged graphs are not drawn again.
    cache: Vec<(String, Value)>,
}

/// The engine that draws graphs.
pub struct Engine(pub Mutex<Py>);
/// A second engine for results and exports, so a long fit never holds up drawing (I3).
pub struct Calc(pub Mutex<Py>);

fn paths(app: &AppHandle) -> Result<(PathBuf, PathBuf), String> {
    let res = app.path().resource_dir().ok();
    let python = match std::env::var_os("DATUM_PYTHON") {
        Some(p) => p.into(),
        None => crate::runtime::python(app)?.unwrap_or_else(|| (if cfg!(windows) { "python" } else { "python3" }).into()),
    };
    let script = res.map(|r| r.join("py").join("worker.py")).filter(|p| p.exists()).unwrap_or_else(|| PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../py/worker.py"));
    Ok((python, script))
}

impl Py {
    fn start(&mut self, app: &AppHandle) -> Result<(), String> {
        let (python, script) = paths(app)?;
        let mut cmd = Command::new(&python);
        cmd.arg("-X").arg("utf8").arg(&script).stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::null());
        // matplotlib keeps its font list here, so only the first start scans the fonts.
        if let Ok(d) = app.path().app_cache_dir() {
            cmd.env("MPLCONFIGDIR", d.join("matplotlib"));
        }
        #[cfg(windows)]
        {
            use std::os::windows::process::CommandExt;
            cmd.creation_flags(0x0800_0000); // CREATE_NO_WINDOW
        }
        let mut child = cmd.spawn().map_err(|e| format!("The graph engine (Python) could not start: {e}. Looked for {}.", python.display()))?;
        let (stdin, stdout) = (child.stdin.take().unwrap(), BufReader::new(child.stdout.take().unwrap()));
        let (tx, lines) = mpsc::channel();
        std::thread::spawn(move || {
            for l in stdout.lines() {
                let Ok(l) = l else { break };
                if tx.send(l).is_err() {
                    break;
                }
            }
        });
        self.worker = Some(Worker { child, stdin, lines });
        let ready = self.read(START).map_err(|e| format!("The graph engine (Python) stopped while starting: {e}"))?;
        if ready["ready"] != true {
            return Err("The graph engine (Python) did not start properly.".into());
        }
        self.versions = self.ask_once(&serde_json::json!({ "cmd": "ping" })).ok();
        self.error = None;
        Ok(())
    }
    fn read(&mut self, wait: Duration) -> Result<Value, String> {
        let w = self.worker.as_mut().ok_or("not running")?;
        match w.lines.recv_timeout(wait) {
            Ok(line) => serde_json::from_str(&line).map_err(|e| e.to_string()),
            Err(mpsc::RecvTimeoutError::Timeout) => {
                self.stop();
                Err(format!("it took longer than {} s and was restarted", wait.as_secs()))
            }
            Err(_) => {
                self.stop();
                Err("the engine closed".into())
            }
        }
    }
    fn ask_once(&mut self, q: &Value) -> Result<Value, String> {
        let w = self.worker.as_mut().ok_or("not running")?;
        if writeln!(w.stdin, "{q}").and_then(|_| w.stdin.flush()).is_err() {
            self.stop();
            return Err("the engine closed".into());
        }
        let r = self.read(REQUEST)?;
        if r["ok"] == true { Ok(r) } else { Err(r["error"].as_str().unwrap_or("The graph engine failed.").to_string()) }
    }
    fn stop(&mut self) {
        if let Some(mut w) = self.worker.take() {
            let _ = w.child.kill();
            let _ = w.child.wait();
        }
    }
    /// Sends a request, starting (or restarting once) the worker if needed.
    pub fn ask(&mut self, app: &AppHandle, q: &Value) -> Result<Value, String> {
        for _ in 0..2 {
            if self.worker.is_none() {
                if let Err(e) = self.start(app) {
                    self.error = Some(e.clone());
                    return Err(e);
                }
            }
            match self.ask_once(q) {
                Err(e) if e.contains("longer than") => return Err(format!("The graph engine stopped: {e}.")),
                Err(e) if self.worker.is_none() => self.error = Some(e),
                r => return r,
            }
        }
        Err(format!("The graph engine stopped: {}", self.error.clone().unwrap_or_default()))
    }
    /// Stops the worker and starts a fresh one (Tools › Restart Engine).
    pub fn restart(&mut self, app: &AppHandle) -> Result<Value, String> {
        self.stop();
        self.cache.clear();
        self.ask(app, &serde_json::json!({ "cmd": "ping" }))
    }
    /// A graph render, from the cache when nothing changed.
    pub fn render(&mut self, app: &AppHandle, q: Value) -> Result<Value, String> {
        let key = q.to_string();
        if let Some((_, v)) = self.cache.iter().find(|(k, _)| *k == key) {
            return Ok(v.clone());
        }
        let v = self.ask(app, &q)?;
        self.cache.insert(0, (key, v.clone()));
        self.cache.truncate(24);
        Ok(v)
    }
}

impl Drop for Py {
    fn drop(&mut self) {
        self.stop();
    }
}
