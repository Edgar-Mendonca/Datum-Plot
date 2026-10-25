//! The Python runtime pack: embeddable CPython with numpy, SciPy, matplotlib and the other
//! libraries, unpacked from `runtime.zip` (inside every installer) into the user's data folder
//! (`runtime/N`, N from py/runtime.txt). It is unpacked again only when N changes.
use serde_json::json;
use std::path::{Path, PathBuf};
use tauri::{AppHandle, Emitter, Manager};

pub fn number() -> u32 {
    include_str!("../../py/runtime.txt").trim().parse().unwrap_or(1)
}

fn root(app: &AppHandle) -> Option<PathBuf> {
    app.path().app_local_data_dir().ok().map(|d| d.join("runtime"))
}

fn status(app: &AppHandle, text: &str) {
    let _ = app.emit("engine", json!({ "versions": null, "error": null, "status": text }));
}

/// Unpacks a runtime zip into `dest` (a fresh folder); `progress` gets whole percents.
fn unzip(zip: &Path, dest: &Path, progress: &dyn Fn(usize)) -> Result<(), String> {
    let f = std::fs::File::open(zip).map_err(|e| e.to_string())?;
    let mut a = zip::ZipArchive::new(f).map_err(|e| format!("The Python runtime file is damaged: {e}"))?;
    let n = a.len();
    for i in 0..n {
        let mut file = a.by_index(i).map_err(|e| e.to_string())?;
        let Some(rel) = file.enclosed_name() else { continue };
        let out = dest.join(rel);
        if file.is_dir() {
            std::fs::create_dir_all(&out).map_err(|e| e.to_string())?;
        } else {
            if let Some(p) = out.parent() {
                std::fs::create_dir_all(p).map_err(|e| e.to_string())?;
            }
            let mut w = std::fs::File::create(&out).map_err(|e| e.to_string())?;
            std::io::copy(&mut file, &mut w).map_err(|e| e.to_string())?;
        }
        if i % 400 == 0 {
            progress(i * 100 / n.max(1));
        }
    }
    Ok(())
}

/// The bundled python.exe, preparing the runtime first if needed. None on other systems and in
/// development, where the Python on the PATH is used.
pub fn python(app: &AppHandle) -> Result<Option<PathBuf>, String> {
    if !cfg!(windows) || cfg!(debug_assertions) {
        return Ok(None);
    }
    let root = root(app).ok_or("No data folder for the Python runtime.")?;
    let n = number();
    let dir = root.join(n.to_string());
    let exe = dir.join("python.exe");
    let bundled = app.path().resource_dir().ok().map(|r| r.join("runtime.zip")).filter(|p| p.exists());
    if exe.exists() {
        // A reinstall can bring the zip back; it is not needed.
        if let Some(z) = bundled {
            let _ = std::fs::remove_file(z);
        }
        return Ok(Some(exe));
    }
    std::fs::create_dir_all(&root).map_err(|e| e.to_string())?;
    let zip = bundled.ok_or("The Python engine is missing. Download the installer again from the Datum Plot releases page and run it.")?;
    let tmp = root.join(format!("{n}.part"));
    let _ = std::fs::remove_dir_all(&tmp);
    unzip(&zip, &tmp, &|p| status(app, &format!("Preparing the Python engine (first start only)… {p}%")))?;
    // The zip is not needed once unpacked (the next installer brings it again).
    let _ = std::fs::remove_file(&zip);
    // 0.1.0 kept Python in the program folder; that copy is no longer used.
    if let Some(old) = app.path().resource_dir().ok().map(|r| r.join("python")).filter(|p| p.join("python.exe").exists()) {
        let _ = std::fs::remove_dir_all(old);
    }
    std::fs::rename(&tmp, &dir).map_err(|e| format!("Could not set up the Python runtime: {e}"))?;
    // Older runtimes are no longer needed.
    for e in std::fs::read_dir(&root).into_iter().flatten().flatten() {
        if e.file_name() != *n.to_string() {
            let _ = std::fs::remove_dir_all(e.path());
        }
    }
    if !exe.exists() {
        return Err("The Python runtime is incomplete. Reinstall Datum Plot.".into());
    }
    Ok(Some(exe))
}

#[cfg(test)]
mod tests {
    use std::io::Write;

    #[test]
    fn unzip_keeps_folders_and_refuses_paths_outside() {
        let dir = std::env::temp_dir().join("datum-plot-unzip-test");
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();
        let zip = dir.join("rt.zip");
        let mut w = zip::ZipWriter::new(std::fs::File::create(&zip).unwrap());
        let o = zip::write::SimpleFileOptions::default();
        for (name, text) in [("python.exe", "py"), ("Lib/site-packages/numpy/__init__.py", "np"), ("../evil.txt", "x")] {
            w.start_file(name, o).unwrap();
            w.write_all(text.as_bytes()).unwrap();
        }
        w.finish().unwrap();
        let out = dir.join("out");
        let seen = std::cell::Cell::new(false);
        super::unzip(&zip, &out, &|_| seen.set(true)).unwrap();
        assert_eq!(std::fs::read_to_string(out.join("Lib/site-packages/numpy/__init__.py")).unwrap(), "np");
        assert!(out.join("python.exe").exists() && seen.get());
        assert!(!dir.join("evil.txt").exists(), "entries outside the folder are skipped");
        let _ = std::fs::remove_dir_all(&dir);
    }
}
