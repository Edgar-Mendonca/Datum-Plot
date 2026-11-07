//! The Windows side: a "Datum Plot Graph" OLE object (IOleObject, IDataObject, IPersistStorage), its class
//! factory for documents that start Datum Plot, the clipboard copy, and the per-user registration.
#![allow(non_snake_case)] // COM method names

use std::cell::RefCell;
use std::mem::ManuallyDrop;

use windows::core::{implement, w, AsImpl, IUnknown, IUnknownImpl, Interface, Ref, BOOL, GUID, HRESULT, PCWSTR, PWSTR};
use windows::Win32::Foundation::{
    CLASS_E_NOAGGREGATION, DATA_S_SAMEFORMATETC, DV_E_FORMATETC, E_FAIL, E_NOTIMPL, HGLOBAL, HWND, POINTL, RECT, S_FALSE, S_OK, SIZE,
};
use windows::Win32::Graphics::Gdi::{
    CloseEnhMetaFile, CreateEnhMetaFileW, GetDC, GetDeviceCaps, GetWinMetaFileBits, ReleaseDC, SetMetaFileBitsEx, StretchDIBits, BITMAPINFO,
    BITMAPINFOHEADER, BI_RGB, DIB_RGB_COLORS, HENHMETAFILE, HORZRES, HORZSIZE, LOGPALETTE, MM_ANISOTROPIC, SRCCOPY, VERTRES, VERTSIZE,
};
use windows::Win32::System::Com::StructuredStorage::{
    CreateILockBytesOnHGlobal, IPersistStorage, IPersistStorage_Impl, IStorage, StgCreateDocfileOnILockBytes, WriteClassStg, WriteFmtUserTypeStg,
};
use windows::Win32::System::Com::{
    CoDisconnectObject, CoRegisterClassObject, CreateDataAdviseHolder, CoRevokeClassObject, IAdviseSink, IClassFactory, IClassFactory_Impl, IDataAdviseHolder, IDataObject,
    IDataObject_Impl, IEnumFORMATETC, IEnumSTATDATA, IMoniker, IPersist_Impl, CLSCTX_LOCAL_SERVER, DATADIR_GET, DVASPECT, DVASPECT_CONTENT, FORMATETC,
    REGCLS_SINGLEUSE, STGMEDIUM, STGMEDIUM_0, STGM_CREATE, STGM_READ, STGM_READWRITE, STGM_SHARE_EXCLUSIVE, TYMED_ENHMF, TYMED_HGLOBAL,
    TYMED_ISTORAGE, TYMED_MFPICT,
};
use windows::Win32::System::DataExchange::{RegisterClipboardFormatW, METAFILEPICT};
use windows::Win32::System::Memory::{GlobalAlloc, GlobalLock, GlobalUnlock, GMEM_MOVEABLE};
use windows::Win32::System::Ole::{
    CreateOleAdviseHolder, IEnumOLEVERB, IOleAdviseHolder, IOleClientSite, IOleObject, IOleObject_Impl, OleFlushClipboard,
    OleRegEnumVerbs, OleRegGetUserType, OleSetClipboard, CF_DIB, CF_ENHMETAFILE, CF_METAFILEPICT, OBJECTDESCRIPTOR,
    OLECLOSE, OLECLOSE_NOSAVE, OLEGETMONIKER, OLEMISC, OLEWHICHMK, USERCLASSTYPE,
};
use windows::Win32::System::Registry::{RegDeleteTreeW, RegSetKeyValueW, HKEY_CURRENT_USER, REG_SZ};
use windows::Win32::UI::Shell::SHCreateStdEnumFmtEtc;
use windows::Win32::UI::WindowsAndMessaging::MSG;

use crate::{Host, Picture};

/// The class of "Datum Plot Graph" objects (fixed for ever: documents store it).
pub const CLSID: GUID = GUID::from_u128(0x5f0c2b7e_8a1d_4c3e_9b6a_0d17a7e2c341);
const PROGID: &str = "DatumPlot.Graph.1";
const NAME: &str = "Datum Plot Graph";
const DATA: PCWSTR = w!("DatumPlot");
const PICTURE: PCWSTR = w!("DatumPlotPicture");

/// The window that shows the graph: reachable from whichever thread the document's calls arrive on (0.3.19: it was
/// per thread, so a document's DoVerb found no window and failed with "unknown error").
static HOST: std::sync::Mutex<Option<Box<dyn Host>>> = std::sync::Mutex::new(None);
fn host() -> std::sync::MutexGuard<'static, Option<Box<dyn Host>>> {
    HOST.lock().unwrap_or_else(std::sync::PoisonError::into_inner)
}

/// Which thread and apartment a call runs in (for the log).
fn here() -> String {
    let mut t = windows::Win32::System::Com::APTTYPE::default();
    let mut q = windows::Win32::System::Com::APTTYPEQUALIFIER::default();
    let apt = unsafe { windows::Win32::System::Com::CoGetApartmentType(&mut t, &mut q) }.map(|_| t.0).unwrap_or(-9);
    format!("[thread {:?}, apartment {apt}]", std::thread::current().id())
}

thread_local! {
    static CURRENT: RefCell<Option<IOleObject>> = const { RefCell::new(None) };
    static COOKIE: RefCell<Option<u32>> = const { RefCell::new(None) };
}

/// 0.3.20: every step is written to a log (embed.log in the app's data folder), so a failure inside a document
/// can be traced. Lines carry the process id: the copy started by the document has its own.
static LOG: std::sync::Mutex<Option<std::path::PathBuf>> = std::sync::Mutex::new(None);

/// Where the log goes (the shell sets it at start).
pub fn log_to(path: std::path::PathBuf) {
    *LOG.lock().unwrap_or_else(std::sync::PoisonError::into_inner) = Some(path);
}

/// Appends one line to the log (kept under about 1 MB: an older half is dropped).
pub fn log(msg: &str) {
    let Some(path) = LOG.lock().unwrap_or_else(std::sync::PoisonError::into_inner).clone() else { return };
    if std::fs::metadata(&path).map(|m| m.len() > 1 << 20).unwrap_or(false) {
        let _ = std::fs::rename(&path, path.with_extension("old.log"));
    }
    let secs = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.as_secs_f64()).unwrap_or(0.0);
    if let Ok(mut f) = std::fs::OpenOptions::new().create(true).append(true).open(&path) {
        use std::io::Write;
        let _ = writeln!(f, "{secs:.3} pid {} {msg}", std::process::id());
    }
}

fn logged<T>(what: &str, r: windows::core::Result<T>) -> windows::core::Result<T> {
    match &r {
        Ok(_) => log(&format!("{what}: ok")),
        Err(e) => log(&format!("{what}: FAILED {}", text(e.clone()))),
    }
    r
}

fn hr<T>(e: HRESULT) -> windows::core::Result<T> {
    Err(e.into())
}
fn text(e: windows::core::Error) -> String {
    format!("{} ({:#010x})", e.message(), e.code().0)
}
fn guid_text(g: &GUID) -> String {
    let v = g.to_u128();
    format!("{{{:08X}-{:04X}-{:04X}-{:04X}-{:012X}}}", v >> 96, (v >> 80) & 0xFFFF, (v >> 64) & 0xFFFF, (v >> 48) & 0xFFFF, v & 0xFFFF_FFFF_FFFF)
}
fn wide(s: &str) -> Vec<u16> {
    s.encode_utf16().chain(Some(0)).collect()
}
fn cf(name: PCWSTR) -> u16 {
    unsafe { RegisterClipboardFormatW(name) as u16 }
}
fn himetric(p: &Picture) -> SIZE {
    SIZE { cx: (p.mm.0 * 100.0).round() as i32, cy: (p.mm.1 * 100.0).round() as i32 }
}

// ---------------------------------------------------------------------------------------------------------------
// Registration (per user, every start: no administrator rights, and a moved install keeps working)

/// Registers "Datum Plot Graph" for this user so documents can start `exe` to edit their graphs.
pub fn register(exe: &std::path::Path) -> Result<(), String> {
    let exe = exe.display().to_string();
    let clsid = format!("Software\\Classes\\CLSID\\{}", guid_text(&CLSID));
    let entries: Vec<(String, Option<&str>, String)> = vec![
        (format!("Software\\Classes\\{PROGID}"), None, NAME.into()),
        (format!("Software\\Classes\\{PROGID}\\CLSID"), None, guid_text(&CLSID)),
        (format!("Software\\Classes\\{PROGID}\\Insertable"), None, String::new()),
        ("Software\\Classes\\DatumPlot.Graph".into(), None, NAME.into()),
        ("Software\\Classes\\DatumPlot.Graph\\CLSID".into(), None, guid_text(&CLSID)),
        ("Software\\Classes\\DatumPlot.Graph\\CurVer".into(), None, PROGID.into()),
        (clsid.clone(), None, NAME.into()),
        (format!("{clsid}\\ProgID"), None, PROGID.into()),
        (format!("{clsid}\\VersionIndependentProgID"), None, "DatumPlot.Graph".into()),
        (format!("{clsid}\\LocalServer32"), None, format!("\"{exe}\"")),
        (format!("{clsid}\\InprocHandler32"), None, "ole32.dll".into()),
        (format!("{clsid}\\Insertable"), None, String::new()),
        (format!("{clsid}\\DefaultIcon"), None, format!("\"{exe}\",0")),
        (format!("{clsid}\\MiscStatus"), None, "0".into()),
        (format!("{clsid}\\Verb\\0"), None, "&Edit,0,2".into()),
        (format!("{clsid}\\Verb\\1"), None, "&Open,0,2".into()),
        (format!("{clsid}\\AuxUserType\\2"), None, "Graph".into()),
        (format!("{clsid}\\AuxUserType\\3"), None, "Datum Plot".into()),
        (format!("{clsid}\\DataFormats\\GetSet\\0"), None, "3,1,32,1".into()), // metafile picture, content, MFPICT, get
        (format!("{clsid}\\DataFormats\\GetSet\\1"), None, "14,1,64,1".into()), // enhanced metafile
        (format!("{clsid}\\DataFormats\\GetSet\\2"), None, "8,1,1,1".into()), // DIB
    ];
    for (key, value, data) in entries {
        let (k, d) = (wide(&key), wide(&data));
        let v = value.map(wide);
        let name = v.as_ref().map_or(PCWSTR::null(), |v| PCWSTR(v.as_ptr()));
        let err = unsafe { RegSetKeyValueW(HKEY_CURRENT_USER, PCWSTR(k.as_ptr()), name, REG_SZ.0, Some(d.as_ptr().cast()), (d.len() * 2) as u32) };
        if err.is_err() {
            return Err(format!("Could not register embedded graphs ({key}): error {}", err.0));
        }
    }
    Ok(())
}

/// Removes the registration (the uninstaller does the same).
pub fn unregister() {
    for key in [format!("Software\\Classes\\CLSID\\{}", guid_text(&CLSID)), format!("Software\\Classes\\{PROGID}"), "Software\\Classes\\DatumPlot.Graph".into()] {
        let k = wide(&key);
        unsafe {
            let _ = RegDeleteTreeW(HKEY_CURRENT_USER, PCWSTR(k.as_ptr()));
        }
    }
}

// ---------------------------------------------------------------------------------------------------------------
// Pictures for documents: an enhanced metafile (sharp at any size, holding the bitmap), a classic metafile and a DIB

/// Bottom-up 24-bit rows on white (alpha composited), each padded to 4 bytes.
fn bgr_rows(p: &Picture) -> (Vec<u8>, u32) {
    let (w, h) = (p.width as usize, p.height as usize);
    let stride = (w * 3).div_ceil(4) * 4;
    let mut out = vec![255u8; stride * h];
    for y in 0..h {
        let row = &mut out[(h - 1 - y) * stride..];
        for x in 0..w {
            let i = (y * w + x) * 4;
            let Some(px) = p.rgba.get(i..i + 4) else { continue };
            let a = px[3] as u32;
            let mix = |c: u8| ((c as u32 * a + 255 * (255 - a)) / 255) as u8;
            row[x * 3] = mix(px[2]);
            row[x * 3 + 1] = mix(px[1]);
            row[x * 3 + 2] = mix(px[0]);
        }
    }
    (out, stride as u32)
}

fn header(p: &Picture) -> BITMAPINFOHEADER {
    let ppm = |px: u32, mm: f64| if mm > 0.0 { (px as f64 / mm * 1000.0).round() as i32 } else { 11811 };
    BITMAPINFOHEADER {
        biSize: std::mem::size_of::<BITMAPINFOHEADER>() as u32,
        biWidth: p.width as i32,
        biHeight: p.height as i32,
        biPlanes: 1,
        biBitCount: 24,
        biCompression: BI_RGB.0,
        biXPelsPerMeter: ppm(p.width, p.mm.0),
        biYPelsPerMeter: ppm(p.height, p.mm.1),
        ..Default::default()
    }
}

fn global(bytes: &[u8]) -> windows::core::Result<HGLOBAL> {
    unsafe {
        let h = GlobalAlloc(GMEM_MOVEABLE, bytes.len().max(1))?;
        let ptr = GlobalLock(h) as *mut u8;
        if ptr.is_null() {
            return hr(E_FAIL);
        }
        std::ptr::copy_nonoverlapping(bytes.as_ptr(), ptr, bytes.len());
        let _ = GlobalUnlock(h);
        Ok(h)
    }
}

fn dib(p: &Picture) -> windows::core::Result<HGLOBAL> {
    let (rows, _) = bgr_rows(p);
    let h = header(p);
    let mut bytes = unsafe { std::slice::from_raw_parts((&h as *const BITMAPINFOHEADER).cast::<u8>(), std::mem::size_of::<BITMAPINFOHEADER>()) }.to_vec();
    bytes.extend_from_slice(&rows);
    global(&bytes)
}

fn emf(p: &Picture) -> windows::core::Result<HENHMETAFILE> {
    if p.width == 0 || p.height == 0 {
        return hr(E_FAIL);
    }
    let s = himetric(p);
    let (rows, _) = bgr_rows(p);
    let bmi = BITMAPINFO { bmiHeader: header(p), ..Default::default() };
    unsafe {
        let frame = RECT { left: 0, top: 0, right: s.cx, bottom: s.cy };
        let hdc = CreateEnhMetaFileW(None, PCWSTR::null(), Some(&frame as *const RECT), PCWSTR::null());
        if hdc.is_invalid() {
            return hr(E_FAIL);
        }
        // The metafile counts in the reference screen's pixels: the picture fills its frame in millimetres.
        let screen = GetDC(None);
        let px = |res, size| GetDeviceCaps(Some(screen), res) as f64 / GetDeviceCaps(Some(screen), size).max(1) as f64;
        let (dw, dh) = ((p.mm.0 * px(HORZRES, HORZSIZE)).round() as i32, (p.mm.1 * px(VERTRES, VERTSIZE)).round() as i32);
        ReleaseDC(None, screen);
        StretchDIBits(hdc, 0, 0, dw, dh, 0, 0, p.width as i32, p.height as i32, Some(rows.as_ptr().cast()), &bmi, DIB_RGB_COLORS, SRCCOPY);
        let m = CloseEnhMetaFile(hdc);
        if m.is_invalid() { hr(E_FAIL) } else { Ok(m) }
    }
}

fn metafile_pict(p: &Picture) -> windows::core::Result<HGLOBAL> {
    let e = emf(p)?;
    unsafe {
        let screen = GetDC(None);
        let n = GetWinMetaFileBits(e, None, MM_ANISOTROPIC.0, screen);
        let mut buf = vec![0u8; n as usize];
        GetWinMetaFileBits(e, Some(&mut buf), MM_ANISOTROPIC.0, screen);
        ReleaseDC(None, screen);
        let _ = windows::Win32::Graphics::Gdi::DeleteEnhMetaFile(Some(e));
        let hmf = SetMetaFileBitsEx(&buf);
        if hmf.is_invalid() {
            return hr(E_FAIL);
        }
        let s = himetric(p);
        let mfp = METAFILEPICT { mm: MM_ANISOTROPIC.0, xExt: s.cx, yExt: s.cy, hMF: hmf };
        global(std::slice::from_raw_parts((&mfp as *const METAFILEPICT).cast::<u8>(), std::mem::size_of::<METAFILEPICT>()))
    }
}

fn descriptor(p: &Picture) -> windows::core::Result<HGLOBAL> {
    let (full, src) = (wide(NAME), wide("Datum Plot"));
    let base = std::mem::size_of::<OBJECTDESCRIPTOR>();
    let d = OBJECTDESCRIPTOR {
        cbSize: (base + (full.len() + src.len()) * 2) as u32,
        clsid: CLSID,
        dwDrawAspect: DVASPECT_CONTENT.0,
        sizel: himetric(p),
        pointl: POINTL::default(),
        dwStatus: 0,
        dwFullUserTypeName: base as u32,
        dwSrcOfCopy: (base + full.len() * 2) as u32,
    };
    let mut bytes = unsafe { std::slice::from_raw_parts((&d as *const OBJECTDESCRIPTOR).cast::<u8>(), base) }.to_vec();
    for c in full.iter().chain(src.iter()) {
        bytes.extend_from_slice(&c.to_le_bytes());
    }
    global(&bytes)
}

// ---------------------------------------------------------------------------------------------------------------
// The storage a document keeps: the project (JSON) and the picture (size, millimetres, RGBA)

fn write_stream(stg: &IStorage, name: PCWSTR, bytes: &[u8]) -> windows::core::Result<()> {
    unsafe {
        let s = stg.CreateStream(name, STGM_CREATE | STGM_READWRITE | STGM_SHARE_EXCLUSIVE, 0, 0)?;
        for chunk in bytes.chunks(1 << 20) {
            s.Write(chunk.as_ptr().cast(), chunk.len() as u32, None).ok()?;
        }
        Ok(())
    }
}

fn read_stream(stg: &IStorage, name: PCWSTR) -> windows::core::Result<Vec<u8>> {
    unsafe {
        let s = stg.OpenStream(name, None, STGM_READ | STGM_SHARE_EXCLUSIVE, 0)?;
        let (mut out, mut buf) = (Vec::new(), vec![0u8; 1 << 16]);
        loop {
            let mut n = 0u32;
            s.Read(buf.as_mut_ptr().cast(), buf.len() as u32, Some(&mut n)).ok()?;
            if n == 0 {
                break;
            }
            out.extend_from_slice(&buf[..n as usize]);
            if out.len() > 512 << 20 {
                return hr(E_FAIL); // a damaged object: never read without end
            }
        }
        Ok(out)
    }
}

fn picture_bytes(p: &Picture) -> Vec<u8> {
    let mut b = Vec::with_capacity(24 + p.rgba.len());
    b.extend_from_slice(&p.width.to_le_bytes());
    b.extend_from_slice(&p.height.to_le_bytes());
    b.extend_from_slice(&p.mm.0.to_le_bytes());
    b.extend_from_slice(&p.mm.1.to_le_bytes());
    b.extend_from_slice(&p.rgba);
    b
}

fn picture_from(b: &[u8]) -> Option<Picture> {
    let u = |i: usize| -> Option<u32> { Some(u32::from_le_bytes(b.get(i..i + 4)?.try_into().ok()?)) };
    let f = |i: usize| -> Option<f64> { Some(f64::from_le_bytes(b.get(i..i + 8)?.try_into().ok()?)) };
    let (width, height) = (u(0)?, u(4)?);
    let rgba = b.get(24..)?.to_vec();
    (rgba.len() == width as usize * height as usize * 4).then(|| Picture { rgba, width, height, mm: (f(8).unwrap_or(80.0), f(16).unwrap_or(60.0)), png: vec![] })
}

fn save_into(stg: &IStorage, data: &[u8], pic: &Picture) -> windows::core::Result<()> {
    unsafe {
        WriteClassStg(stg, &CLSID)?;
        WriteFmtUserTypeStg(stg, cf(w!("Datum Plot Graph")), w!("Datum Plot Graph"))?;
    }
    write_stream(stg, DATA, data)?;
    write_stream(stg, PICTURE, &picture_bytes(pic))
}

// ---------------------------------------------------------------------------------------------------------------
// The object

#[derive(Default)]
struct State {
    data: Vec<u8>,
    pic: Picture,
    site: Option<IOleClientSite>,
    ole: Option<IOleAdviseHolder>,
    dat: Option<IDataAdviseHolder>,
    dirty: bool,
    container: String,
}

#[implement(IOleObject, IDataObject, IPersistStorage)]
struct Graph {
    s: RefCell<State>,
}

/// The formats a document can take: the object itself first, then pictures for programs that only paste pictures.
fn formats() -> Vec<FORMATETC> {
    let f = |cf: u16, tymed: i32| FORMATETC { cfFormat: cf, ptd: std::ptr::null_mut(), dwAspect: DVASPECT_CONTENT.0, lindex: -1, tymed: tymed as u32 };
    vec![
        f(cf(w!("Embed Source")), TYMED_ISTORAGE.0),
        f(cf(w!("Object Descriptor")), TYMED_HGLOBAL.0),
        f(CF_ENHMETAFILE.0, TYMED_ENHMF.0),
        f(CF_METAFILEPICT.0, TYMED_MFPICT.0),
        f(CF_DIB.0, TYMED_HGLOBAL.0),
        f(cf(w!("PNG")), TYMED_HGLOBAL.0),
    ]
}

fn medium(tymed: i32, u: STGMEDIUM_0) -> STGMEDIUM {
    STGMEDIUM { tymed: tymed as u32, u, pUnkForRelease: ManuallyDrop::new(None) }
}

impl Graph_Impl {
    fn advise_holder(&self) -> windows::core::Result<IOleAdviseHolder> {
        if let Some(h) = self.s.borrow().ole.clone() {
            return Ok(h);
        }
        let h = unsafe { CreateOleAdviseHolder()? };
        self.s.borrow_mut().ole = Some(h.clone());
        Ok(h)
    }
    fn data_holder(&self) -> windows::core::Result<IDataAdviseHolder> {
        if let Some(h) = self.s.borrow().dat.clone() {
            return Ok(h);
        }
        let h = unsafe { CreateDataAdviseHolder()? };
        self.s.borrow_mut().dat = Some(h.clone());
        Ok(h)
    }
}

impl IDataObject_Impl for Graph_Impl {
    fn GetData(&self, f: *const FORMATETC) -> windows::core::Result<STGMEDIUM> {
        let f = unsafe { f.as_ref() }.ok_or(windows::core::Error::from(DV_E_FORMATETC))?;
        log(&format!("GetData format {} medium {}", f.cfFormat, f.tymed));
        let (data, pic) = {
            let s = self.s.borrow();
            (s.data.clone(), s.pic.clone())
        };
        let want = |t: i32| f.tymed & t as u32 != 0;
        if f.cfFormat == cf(w!("Embed Source")) && want(TYMED_ISTORAGE.0) {
            let stg = unsafe {
                let lb = CreateILockBytesOnHGlobal(None, true)?;
                StgCreateDocfileOnILockBytes(&lb, STGM_CREATE | STGM_READWRITE | STGM_SHARE_EXCLUSIVE, 0)?
            };
            save_into(&stg, &data, &pic)?;
            return Ok(medium(TYMED_ISTORAGE.0, STGMEDIUM_0 { pstg: ManuallyDrop::new(Some(stg)) }));
        }
        if f.cfFormat == cf(w!("Object Descriptor")) && want(TYMED_HGLOBAL.0) {
            return Ok(medium(TYMED_HGLOBAL.0, STGMEDIUM_0 { hGlobal: descriptor(&pic)? }));
        }
        if f.cfFormat == CF_ENHMETAFILE.0 && want(TYMED_ENHMF.0) {
            return Ok(medium(TYMED_ENHMF.0, STGMEDIUM_0 { hEnhMetaFile: emf(&pic)? }));
        }
        if f.cfFormat == CF_METAFILEPICT.0 && want(TYMED_MFPICT.0) {
            return Ok(medium(TYMED_MFPICT.0, STGMEDIUM_0 { hMetaFilePict: metafile_pict(&pic)?.0 }));
        }
        if f.cfFormat == CF_DIB.0 && want(TYMED_HGLOBAL.0) {
            return Ok(medium(TYMED_HGLOBAL.0, STGMEDIUM_0 { hGlobal: dib(&pic)? }));
        }
        if f.cfFormat == cf(w!("PNG")) && want(TYMED_HGLOBAL.0) && !pic.png.is_empty() {
            return Ok(medium(TYMED_HGLOBAL.0, STGMEDIUM_0 { hGlobal: global(&pic.png)? }));
        }
        hr(DV_E_FORMATETC)
    }
    fn GetDataHere(&self, f: *const FORMATETC, m: *mut STGMEDIUM) -> windows::core::Result<()> {
        let (f, m) = unsafe { (f.as_ref(), m.as_ref()) };
        let (Some(f), Some(m)) = (f, m) else { return hr(DV_E_FORMATETC) };
        if f.cfFormat != cf(w!("Embed Source")) || m.tymed != TYMED_ISTORAGE.0 as u32 {
            return hr(DV_E_FORMATETC);
        }
        let stg = unsafe { (*m.u.pstg).clone() }.ok_or(windows::core::Error::from(E_FAIL))?;
        let (data, pic) = {
            let s = self.s.borrow();
            (s.data.clone(), s.pic.clone())
        };
        save_into(&stg, &data, &pic)
    }
    fn QueryGetData(&self, f: *const FORMATETC) -> HRESULT {
        let Some(f) = (unsafe { f.as_ref() }) else { return DV_E_FORMATETC };
        let png = !self.s.borrow().pic.png.is_empty();
        let ok = formats().iter().any(|x| x.cfFormat == f.cfFormat && f.tymed & x.tymed != 0 && (png || x.cfFormat != cf(w!("PNG"))));
        if ok { S_OK } else { DV_E_FORMATETC }
    }
    fn GetCanonicalFormatEtc(&self, _i: *const FORMATETC, o: *mut FORMATETC) -> HRESULT {
        if let Some(o) = unsafe { o.as_mut() } {
            o.ptd = std::ptr::null_mut();
        }
        DATA_S_SAMEFORMATETC
    }
    fn SetData(&self, _f: *const FORMATETC, _m: *const STGMEDIUM, _r: BOOL) -> windows::core::Result<()> {
        hr(E_NOTIMPL)
    }
    fn EnumFormatEtc(&self, dir: u32) -> windows::core::Result<IEnumFORMATETC> {
        if dir != DATADIR_GET.0 as u32 {
            return hr(E_NOTIMPL);
        }
        let mut f = formats();
        if self.s.borrow().pic.png.is_empty() {
            f.pop();
        }
        unsafe { SHCreateStdEnumFmtEtc(&f) }
    }
    fn DAdvise(&self, f: *const FORMATETC, advf: u32, sink: Ref<IAdviseSink>) -> windows::core::Result<u32> {
        let me: IDataObject = self.to_interface();
        unsafe { self.data_holder()?.Advise(&me, f, advf, sink.ok()?) }
    }
    fn DUnadvise(&self, c: u32) -> windows::core::Result<()> {
        unsafe { self.data_holder()?.Unadvise(c) }
    }
    fn EnumDAdvise(&self) -> windows::core::Result<IEnumSTATDATA> {
        unsafe { self.data_holder()?.EnumAdvise() }
    }
}

impl IPersist_Impl for Graph_Impl {
    fn GetClassID(&self) -> windows::core::Result<GUID> {
        Ok(CLSID)
    }
}

impl IPersistStorage_Impl for Graph_Impl {
    fn IsDirty(&self) -> HRESULT {
        if self.s.borrow().dirty { S_OK } else { S_FALSE }
    }
    fn InitNew(&self, _stg: Ref<IStorage>) -> windows::core::Result<()> {
        log("InitNew");
        Ok(())
    }
    fn Load(&self, stg: Ref<IStorage>) -> windows::core::Result<()> {
        let stg = logged("Load: the document's storage", stg.ok())?;
        let data = logged("Load: the graph's project", read_stream(stg, DATA))?;
        log(&format!("Load: {} bytes of project", data.len()));
        let pic = read_stream(stg, PICTURE).ok().and_then(|b| picture_from(&b)).unwrap_or_default();
        let mut s = self.s.borrow_mut();
        (s.data, s.pic, s.dirty) = (data, pic, false);
        Ok(())
    }
    fn Save(&self, stg: Ref<IStorage>, _same: BOOL) -> windows::core::Result<()> {
        let (data, pic) = {
            let s = self.s.borrow();
            (s.data.clone(), s.pic.clone())
        };
        save_into(stg.ok()?, &data, &pic)?;
        self.s.borrow_mut().dirty = false;
        Ok(())
    }
    fn SaveCompleted(&self, _stg: Ref<IStorage>) -> windows::core::Result<()> {
        if let Some(h) = self.s.borrow().ole.clone() {
            unsafe {
                let _ = h.SendOnSave();
            }
        }
        Ok(())
    }
    fn HandsOffStorage(&self) -> windows::core::Result<()> {
        Ok(())
    }
}

impl IOleObject_Impl for Graph_Impl {
    fn SetClientSite(&self, site: Ref<IOleClientSite>) -> windows::core::Result<()> {
        log(&format!("SetClientSite ({})", if site.is_null() { "none" } else { "a site" }));
        self.s.borrow_mut().site = site.cloned();
        Ok(())
    }
    fn GetClientSite(&self) -> windows::core::Result<IOleClientSite> {
        self.s.borrow().site.clone().ok_or(windows::core::Error::from(E_FAIL))
    }
    fn SetHostNames(&self, app: &PCWSTR, _obj: &PCWSTR) -> windows::core::Result<()> {
        if !app.is_null() {
            self.s.borrow_mut().container = unsafe { app.to_string() }.unwrap_or_default();
        }
        log(&format!("SetHostNames: {}", self.s.borrow().container));
        Ok(())
    }
    fn Close(&self, how: &OLECLOSE) -> windows::core::Result<()> {
        log(&format!("Close ({})", how.0));
        let (dirty, site) = {
            let s = self.s.borrow();
            (s.dirty, s.site.clone())
        };
        if dirty && *how != OLECLOSE_NOSAVE {
            if let Some(site) = site {
                unsafe {
                    let _ = site.SaveObject();
                }
            }
        }
        shut(self, self.to_interface());
        if let Some(h) = host().as_ref() {
            h.close()
        }
        Ok(())
    }
    fn SetMoniker(&self, _w: &OLEWHICHMK, _m: Ref<IMoniker>) -> windows::core::Result<()> {
        Ok(())
    }
    fn GetMoniker(&self, _a: &OLEGETMONIKER, _w: &OLEWHICHMK) -> windows::core::Result<IMoniker> {
        hr(E_NOTIMPL)
    }
    fn InitFromData(&self, _d: Ref<IDataObject>, _c: BOOL, _r: u32) -> windows::core::Result<()> {
        hr(E_NOTIMPL)
    }
    fn GetClipboardData(&self, _r: u32) -> windows::core::Result<IDataObject> {
        hr(E_NOTIMPL)
    }
    fn DoVerb(&self, verb: i32, _msg: *const MSG, _site: Ref<IOleClientSite>, _l: i32, _p: HWND, _r: *const RECT) -> windows::core::Result<()> {
        log(&format!("DoVerb {verb} {}", here()));
        if verb == -3 {
            return Ok(()); // hide: the window stays as the user left it
        }
        if verb < -2 {
            return hr(E_NOTIMPL);
        }
        let (site, data, container) = {
            let s = self.s.borrow();
            (s.site.clone(), s.data.clone(), s.container.clone())
        };
        if let Some(site) = site {
            unsafe {
                let _ = site.ShowObject();
                let _ = site.OnShowWindow(true);
            }
        }
        match host().as_ref() {
            Some(h) => {
                h.open(data, container);
                Ok(())
            }
            None => {
                log("DoVerb: no window to show the graph (not started for a document)");
                hr(E_FAIL)
            }
        }
    }
    fn EnumVerbs(&self) -> windows::core::Result<IEnumOLEVERB> {
        unsafe { OleRegEnumVerbs(&CLSID) }
    }
    fn Update(&self) -> windows::core::Result<()> {
        Ok(())
    }
    fn IsUpToDate(&self) -> windows::core::Result<()> {
        Ok(())
    }
    fn GetUserClassID(&self) -> windows::core::Result<GUID> {
        Ok(CLSID)
    }
    fn GetUserType(&self, form: &USERCLASSTYPE) -> windows::core::Result<PWSTR> {
        unsafe { OleRegGetUserType(&CLSID, *form) }
    }
    fn SetExtent(&self, _a: DVASPECT, _s: *const SIZE) -> windows::core::Result<()> {
        Ok(()) // the size comes from the graph (Format Graph › Graph); the document scales the picture
    }
    fn GetExtent(&self, _a: DVASPECT) -> windows::core::Result<SIZE> {
        Ok(himetric(&self.s.borrow().pic))
    }
    fn Advise(&self, sink: Ref<IAdviseSink>) -> windows::core::Result<u32> {
        unsafe { self.advise_holder()?.Advise(sink.ok()?) }
    }
    fn Unadvise(&self, c: u32) -> windows::core::Result<()> {
        unsafe { self.advise_holder()?.Unadvise(c) }
    }
    fn EnumAdvise(&self) -> windows::core::Result<IEnumSTATDATA> {
        unsafe { self.advise_holder()?.EnumAdvise() }
    }
    fn GetMiscStatus(&self, _a: DVASPECT) -> windows::core::Result<OLEMISC> {
        Ok(OLEMISC(0))
    }
    fn SetColorScheme(&self, _p: *const LOGPALETTE) -> windows::core::Result<()> {
        hr(E_NOTIMPL)
    }
}

/// Tells the document the object is closing and lets it go.
fn shut(g: &Graph, me: IUnknown) {
    let (ole, site) = {
        let s = g.s.borrow();
        (s.ole.clone(), s.site.clone())
    };
    unsafe {
        if let Some(h) = ole {
            let _ = h.SendOnClose();
        }
        if let Some(site) = site {
            let _ = site.OnShowWindow(false);
        }
    }
    unsafe {
        let _ = CoDisconnectObject(&me, None);
    }
    CURRENT.with(|c| *c.borrow_mut() = None);
    if let Some(c) = COOKIE.with(|c| c.borrow_mut().take()) {
        unsafe {
            let _ = CoRevokeClassObject(c);
        }
    }
}

// ---------------------------------------------------------------------------------------------------------------
// The class factory, and what the window calls

#[implement(IClassFactory)]
struct Factory;

impl IClassFactory_Impl for Factory_Impl {
    fn CreateInstance(&self, outer: Ref<IUnknown>, riid: *const GUID, out: *mut *mut core::ffi::c_void) -> windows::core::Result<()> {
        unsafe {
            if !out.is_null() {
                *out = std::ptr::null_mut();
            }
        }
        log(&format!("CreateInstance: a document asks for a graph {}", here()));
        if !outer.is_null() {
            return hr(CLASS_E_NOAGGREGATION);
        }
        let g: IOleObject = Graph { s: RefCell::new(State::default()) }.into();
        CURRENT.with(|c| *c.borrow_mut() = Some(g.clone()));
        unsafe { g.query(riid, out).ok() }
    }
    fn LockServer(&self, _lock: BOOL) -> windows::core::Result<()> {
        Ok(())
    }
}

/// Prepares the window's thread for OLE (call once, on that thread, before the message loop runs).
pub fn init() -> Result<(), String> {
    logged("OleInitialize", unsafe { windows::Win32::System::Ole::OleInitialize(None) }).map_err(text)
}

/// Puts the graph on the clipboard as an embeddable object (with pictures for programs that take only pictures).
/// Call on the window's thread after `OleInitialize`.
pub fn copy_embedded(data: &[u8], pic: &Picture) -> Result<(), String> {
    let g: IDataObject = Graph { s: RefCell::new(State { data: data.to_vec(), pic: pic.clone(), ..Default::default() }) }.into();
    unsafe {
        logged("Copy Embedded: clipboard", OleSetClipboard(&g)).map_err(text)?;
        logged("Copy Embedded: flush", OleFlushClipboard()).map_err(text) // the clipboard keeps its own copy, even after Datum Plot closes
    }
}

/// Started for a document (`-Embedding`): offers "Datum Plot Graph" objects to it. Call on the window's thread
/// after `OleInitialize`, before the message loop runs.
pub fn serve(host: Box<dyn Host>) -> Result<(), String> {
    *self::host() = Some(host);
    log(&format!("Serve {}", here()));
    let f: IUnknown = Factory.into();
    let cookie = logged("Serve: CoRegisterClassObject", unsafe { CoRegisterClassObject(&CLSID, &f, CLSCTX_LOCAL_SERVER, REGCLS_SINGLEUSE) }).map_err(text)?;
    COOKIE.with(|c| *c.borrow_mut() = Some(cookie));
    Ok(())
}

/// The window's **Update**: the document receives the new project and picture.
pub fn update(data: Vec<u8>, pic: Picture) -> Result<(), String> {
    let obj = CURRENT.with(|c| c.borrow().clone()).ok_or("This graph is no longer connected to its document.")?;
    let g: &Graph = unsafe { AsImpl::<Graph>::as_impl(&obj) };
    let site = {
        let mut s = g.s.borrow_mut();
        (s.data, s.pic, s.dirty) = (data, pic, true);
        s.site.clone()
    };
    let dat = g.s.borrow().dat.clone();
    log(&format!("Update {}", here()));
    unsafe {
        if let Some(site) = site {
            logged("Update: SaveObject", site.SaveObject()).map_err(text)?;
        } else {
            log("Update: no client site");
        }
        if let Some(h) = dat {
            let me: IDataObject = obj.cast().map_err(text)?;
            let _ = h.SendOnDataChange(&me, None, 0);
        }
    }
    Ok(())
}

/// The window closed: the document is told, and lets the object go.
pub fn closed() {
    log(&format!("Closed by the window {}", here()));
    if let Some(obj) = CURRENT.with(|c| c.borrow().clone()) {
        let g: &Graph = unsafe { AsImpl::<Graph>::as_impl(&obj) };
        let me: IUnknown = obj.cast().unwrap_or_else(|_| obj.clone().into());
        shut(g, me);
    }
}

/// Help › Check Embedded Graphs: starts Datum Plot for a "document" exactly as a document does (through Windows,
/// a second copy with `-Embedding`), hands it a graph, shows it, and closes it. Returns what happened, step by step.
pub fn self_test() -> Result<String, String> {
    std::thread::spawn(|| unsafe {
        use windows::Win32::System::Com::{CoCreateInstance, CoInitializeEx, COINIT_APARTMENTTHREADED};
        let _ = CoInitializeEx(None, COINIT_APARTMENTTHREADED);
        let t0 = std::time::Instant::now();
        log("Check: starting Datum Plot for a document");
        let obj: IOleObject = CoCreateInstance(&CLSID, None, CLSCTX_LOCAL_SERVER)
            .map_err(|e| format!("Windows could not start Datum Plot for a document: {}", text(e)))?;
        let started = t0.elapsed().as_secs_f64();
        let pic = Picture { rgba: vec![255; 16 * 12 * 4], width: 16, height: 12, mm: (80.0, 60.0), png: vec![] };
        let src: IPersistStorage = Graph { s: RefCell::new(State { data: br#"{"name":"Check"}"#.to_vec(), pic, ..Default::default() }) }.into();
        let lb = CreateILockBytesOnHGlobal(None, true).map_err(text)?;
        let stg = StgCreateDocfileOnILockBytes(&lb, STGM_CREATE | STGM_READWRITE | STGM_SHARE_EXCLUSIVE, 0).map_err(text)?;
        src.Save(&stg, true).map_err(text)?;
        let ps: IPersistStorage = obj.cast().map_err(text)?;
        ps.Load(&stg).map_err(|e| format!("Datum Plot started ({started:.1} s) but could not read the graph: {}", text(e)))?;
        let size = obj.GetExtent(DVASPECT_CONTENT).map_err(text)?;
        obj.SetHostNames(w!("the check"), w!("graph")).map_err(text)?;
        obj.DoVerb(0, std::ptr::null(), None, 0, HWND::default(), std::ptr::null())
            .map_err(|e| format!("Datum Plot started and read the graph, but could not show it: {}", text(e)))?;
        std::thread::sleep(std::time::Duration::from_millis(1500));
        let _ = obj.Close(OLECLOSE_NOSAVE);
        log("Check: passed");
        Ok(format!("Datum Plot started for a document in {started:.1} s, read its graph ({} × {} mm), showed it and closed.", size.cx / 100, size.cy / 100))
    })
    .join()
    .unwrap_or_else(|_| Err("The check stopped unexpectedly.".into()))
}

#[cfg(test)]
#[path = "tests.rs"]
mod tests;
