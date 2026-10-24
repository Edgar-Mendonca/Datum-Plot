//! The Python engine (numpy, scipy, matplotlib): one worker process, started at launch and kept
//! running. Requests and answers are single JSON lines (see py/worker.py). The installed app
//! ships its own Python in `resources/python`; a development build uses DATUM_PYTHON or the
//! Python on the PATH.
use serde_json::Value;
use std::io::{BufRead, BufReader, Write};
use std::path::PathBuf;
use std::process::{Child, ChildStdin, ChildStdout, Command, Stdio};
use std::sync::Mutex;
use tauri::{AppHandle, Manager};

pub struct Worker {
    child: Child,
    stdin: ChildStdin,
    stdout: BufReader<ChildStdout>,
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

pub struct Engine(pub Mutex<Py>);

fn paths(app: &AppHandle) -> (PathBuf, PathBuf) {
    let res = app.path().resource_dir().ok();
    let bundled = res.as_ref().map(|r| r.join("python").join(if cfg!(windows) { "python.exe" } else { "bin/python3" })).filter(|p| p.exists());
    let python = std::env::var_os("DATUM_PYTHON").map(PathBuf::from).or(bundled).unwrap_or_else(|| (if cfg!(windows) { "python" } else { "python3" }).into());
    let script = res.map(|r| r.join("py").join("worker.py")).filter(|p| p.exists()).unwrap_or_else(|| PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../py/worker.py"));
    (python, script)
}

impl Py {
    fn start(&mut self, app: &AppHandle) -> Result<(), String> {
        let (python, script) = paths(app);
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
        self.worker = Some(Worker { child, stdin, stdout });
        let ready = self.read().map_err(|e| format!("The graph engine (Python) stopped while starting: {e}"))?;
        if ready["ready"] != true {
            return Err("The graph engine (Python) did not start properly.".into());
        }
        self.versions = self.ask_once(&serde_json::json!({ "cmd": "ping" })).ok();
        self.error = None;
        Ok(())
    }
    fn read(&mut self) -> Result<Value, String> {
        let w = self.worker.as_mut().ok_or("not running")?;
        let mut line = String::new();
        match w.stdout.read_line(&mut line) {
            Ok(0) | Err(_) => {
                self.stop();
                Err("the engine closed".into())
            }
            Ok(_) => serde_json::from_str(&line).map_err(|e| e.to_string()),
        }
    }
    fn ask_once(&mut self, q: &Value) -> Result<Value, String> {
        let w = self.worker.as_mut().ok_or("not running")?;
        if writeln!(w.stdin, "{q}").and_then(|_| w.stdin.flush()).is_err() {
            self.stop();
            return Err("the engine closed".into());
        }
        let r = self.read()?;
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
                Err(e) if self.worker.is_none() => self.error = Some(e),
                r => return r,
            }
        }
        Err(format!("The graph engine stopped: {}", self.error.clone().unwrap_or_default()))
    }
    /// A graph render, from the cache when nothing changed.
    pub fn render(&mut self, app: &AppHandle, q: Value) -> Result<Value, String> {
        let key = q.to_string();
        if let Some((_, v)) = self.cache.iter().find(|(k, _)| *k == key) {
            return Ok(v.clone());
        }
        let v = self.ask(app, &q)?;
        self.cache.insert(0, (key, v.clone()));
        self.cache.truncate(8);
        Ok(v)
    }
}

impl Drop for Py {
    fn drop(&mut self) {
        self.stop();
    }
}
