//! Updates from GitHub Releases: compare versions, download the installer, check its
//! SHA-256 against SHA256SUMS.txt, then run it silently and restart.
use serde::Serialize;
use sha2::{Digest, Sha256};
use std::io::{Read, Write};
use tauri::{AppHandle, Emitter};

const REPO: &str = "Edgar-Mendonca/Datum-Plot";

#[derive(Serialize)]
pub struct Info {
    current: &'static str,
    latest: Option<String>,
    beta: bool,
    available: bool,
    notes: String,
    published: String,
    url: Option<String>,
    sums: Option<String>,
    size: u64,
    page: String,
}

fn agent() -> ureq::Agent {
    ureq::AgentBuilder::new()
        .timeout_connect(std::time::Duration::from_secs(10))
        .timeout_read(std::time::Duration::from_secs(30))
        .try_proxy_from_env(true)
        .user_agent(concat!("DatumPlot/", env!("CARGO_PKG_VERSION")))
        .build()
}

/// 0.3.0-beta.2 → [0, 3, 0, 0, 2]; 0.3.0 → [0, 3, 0, 1, 0], so a release beats its betas.
fn parts(v: &str) -> Vec<u64> {
    let v = v.trim_start_matches('v');
    let (main, pre) = v.split_once('-').unwrap_or((v, ""));
    let mut out: Vec<u64> = main.split('.').map(|p| p.parse().unwrap_or(0)).collect();
    out.resize(3, 0);
    out.push(pre.is_empty() as u64);
    out.push(pre.rsplit('.').next().and_then(|n| n.parse().ok()).unwrap_or(0));
    out
}

/// The newest release; with `beta`, pre-releases count too.
pub fn check(beta: bool) -> Result<Info, String> {
    let current = env!("CARGO_PKG_VERSION");
    let page = format!("https://github.com/{REPO}/releases");
    let none = |page| Info { current, latest: None, beta: false, available: false, notes: String::new(), published: String::new(), url: None, sums: None, size: 0, page };
    let url = if beta { format!("https://api.github.com/repos/{REPO}/releases?per_page=10") } else { format!("https://api.github.com/repos/{REPO}/releases/latest") };
    let rel: serde_json::Value = match agent().get(&url).call() {
        Ok(r) => {
            let v: serde_json::Value = r.into_json().map_err(|e| e.to_string())?;
            match v.as_array() {
                Some(list) => match list.iter().filter(|r| !r["draft"].as_bool().unwrap_or(false)).max_by(|a, b| parts(a["tag_name"].as_str().unwrap_or("")).cmp(&parts(b["tag_name"].as_str().unwrap_or("")))) {
                    Some(r) => r.clone(),
                    None => return Ok(none(page)),
                },
                None => v,
            }
        }
        Err(ureq::Error::Status(404, _)) => return Ok(none(page)),
        Err(ureq::Error::Status(c, _)) => return Err(format!("GitHub answered {c}. Try again later.")),
        Err(_) => return Err("Could not reach GitHub. Check your internet connection.".into()),
    };
    let latest = rel["tag_name"].as_str().unwrap_or("").trim_start_matches('v').to_string();
    let assets = rel["assets"].as_array().cloned().unwrap_or_default();
    let find = |suffix: &str| assets.iter().find(|a| a["name"].as_str().is_some_and(|n| n.to_lowercase().ends_with(suffix)));
    let exe = find("-setup.exe");
    Ok(Info {
        current,
        available: !latest.is_empty() && parts(&latest) > parts(current),
        latest: Some(latest),
        beta: rel["prerelease"].as_bool().unwrap_or(false),
        notes: rel["body"].as_str().unwrap_or("").into(),
        published: rel["published_at"].as_str().unwrap_or("").get(..10).unwrap_or("").into(),
        url: exe.and_then(|a| a["browser_download_url"].as_str()).map(Into::into),
        sums: find("sha256sums.txt").and_then(|a| a["browser_download_url"].as_str()).map(Into::into),
        size: exe.and_then(|a| a["size"].as_u64()).unwrap_or(0),
        page: rel["html_url"].as_str().map(Into::into).unwrap_or(page),
    })
}

/// Downloads `url` to `dest` with progress events, checking its SHA-256 against `sums` (a
/// SHA256SUMS.txt from the same release). Only this repo's release files are accepted.
/// True when SHA256SUMS lists exactly `name` (as `sha256sum` writes it: "hash  name" or "hash *name") with hash `got`.
fn matches(list: &str, name: &str, got: &str) -> bool {
    list.lines().filter_map(|l| l.split_once(char::is_whitespace)).any(|(h, n)| n.trim().trim_start_matches('*') == name && h.len() == 64 && h.eq_ignore_ascii_case(got))
}

pub fn download(app: &AppHandle, url: &str, sums: Option<&str>, dest: &std::path::Path, event: &str) -> Result<(), String> {
    let base = format!("https://github.com/{REPO}/releases/download/");
    if !url.starts_with(&base) || sums.is_some_and(|s| !s.starts_with(&base)) {
        return Err("Files are only downloaded from the Datum Plot releases page.".into());
    }
    // Every release publishes SHA256SUMS.txt: an installer that cannot be checked is not run.
    let Some(sums) = sums else { return Err("This release has no checksum file, so the download cannot be checked. Download it from the releases page instead.".into()) };
    let name = url.rsplit('/').next().unwrap_or("download").to_string();
    let resp = agent().get(url).call().map_err(|e| format!("Download failed: {e}"))?;
    let total: u64 = resp.header("Content-Length").and_then(|v| v.parse().ok()).unwrap_or(0);
    let (mut src, mut file) = (resp.into_reader(), std::fs::File::create(dest).map_err(|e| e.to_string())?);
    let (mut hash, mut buf, mut done, mut last) = (Sha256::new(), vec![0u8; 1 << 16], 0u64, 0u64);
    loop {
        let n = src.read(&mut buf).map_err(|e| format!("Download failed: {e}"))?;
        if n == 0 {
            break;
        }
        file.write_all(&buf[..n]).map_err(|e| e.to_string())?;
        hash.update(&buf[..n]);
        done += n as u64;
        if total > 0 && done * 100 / total > last {
            last = done * 100 / total;
            let _ = app.emit(event, last);
        }
    }
    drop(file);
    let fail = |e: String| format!("Could not fetch checksums: {e}");
    let list = agent().get(sums).call().map_err(|e| fail(e.to_string()))?.into_string().map_err(|e| fail(e.to_string()))?;
    let got: String = hash.finalize().iter().map(|b| format!("{b:02x}")).collect();
    if !matches(&list, &name, &got) {
        let _ = std::fs::remove_file(dest);
        return Err("The download did not match its checksum and was deleted. Try again.".into());
    }
    let _ = app.emit(event, 100u64);
    Ok(())
}

pub fn install(app: &AppHandle, url: &str, sums: Option<&str>) -> Result<(), String> {
    if !cfg!(windows) {
        return Err("Automatic install is for Windows. Download the new version from the releases page.".into());
    }
    let name = url.rsplit('/').next().unwrap_or("DatumPlot-setup.exe").to_string();
    let dest = std::env::temp_dir().join(&name);
    download(app, url, sums, &dest, "update-progress")?;
    launch(&dest)?;
    app.exit(0);
    Ok(())
}

/// Waits for this process to exit, installs silently, then starts the new version.
#[cfg(windows)]
fn launch(installer: &std::path::Path) -> Result<(), String> {
    use std::os::windows::process::CommandExt;
    let exe = std::env::current_exe().map_err(|e| e.to_string())?;
    let line = format!(
        "/C ping -n 3 127.0.0.1 >nul & start \"\" /wait \"{}\" /S & start \"\" \"{}\"",
        installer.display(),
        exe.display()
    );
    std::process::Command::new("cmd")
        .raw_arg(line)
        .creation_flags(0x0800_0000) // CREATE_NO_WINDOW
        .spawn()
        .map_err(|e| format!("Could not start the installer: {e}"))?;
    Ok(())
}

#[cfg(not(windows))]
fn launch(_: &std::path::Path) -> Result<(), String> {
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::matches;
    #[test]
    fn checksums_match_the_exact_file_only() {
        let h = "a".repeat(64);
        let list = format!("{h}  DatumPlot-0.2.23-setup.exe\n{}  evil-DatumPlot-0.2.23-setup.exe\n", "b".repeat(64));
        assert!(matches(&list, "DatumPlot-0.2.23-setup.exe", &h.to_uppercase()));
        assert!(!matches(&list, "DatumPlot-0.2.23-setup.exe", &"b".repeat(64)), "another file's line must not count");
        assert!(matches(&format!("{h} *x.exe"), "x.exe", &h) && !matches("short  x.exe", "x.exe", "short"));
    }
}
