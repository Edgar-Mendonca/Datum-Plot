//! What a document does with a "Datum Plot Graph", without a document program: save and reload the object, read
//! each picture, create the embedded object from the clipboard data (as Paste does) and draw it from its cache.
//! Windows only (CI's Windows job runs them).
use super::*;
use windows::Win32::Graphics::Gdi::{DeleteEnhMetaFile, GetEnhMetaFileBits};
use windows::Win32::System::Com::StructuredStorage::ReadClassStg;
use windows::Win32::System::Ole::ReleaseStgMedium;
use windows::Win32::System::Ole::{OleCreateFromData, OleDraw, OleGetClipboard, OleInitialize, OleLoad, OleSave, OLERENDER_DRAW};

fn picture() -> Picture {
    let (w, h) = (40u32, 30u32);
    let rgba = (0..w * h).flat_map(|i| [(i % 255) as u8, 90, 200, 255]).collect();
    Picture { rgba, width: w, height: h, mm: (80.0, 60.0), png: vec![0x89, b'P', b'N', b'G'] }
}

fn storage() -> IStorage {
    unsafe {
        let lb = CreateILockBytesOnHGlobal(None, true).unwrap();
        StgCreateDocfileOnILockBytes(&lb, STGM_CREATE | STGM_READWRITE | STGM_SHARE_EXCLUSIVE, 0).unwrap()
    }
}

fn graph(data: &[u8]) -> IOleObject {
    Graph { s: RefCell::new(State { data: data.to_vec(), pic: picture(), ..Default::default() }) }.into()
}

fn init() {
    unsafe {
        let _ = OleInitialize(None);
    }
}

#[test]
fn the_object_saves_and_loads_its_project_and_picture() {
    init();
    let data = br#"{"name":"Embedded","tables":[]}"#;
    let stg = storage();
    let a: IPersistStorage = graph(data).cast().unwrap();
    unsafe { a.Save(&stg, true).unwrap() };
    let b = graph(b"");
    let bp: IPersistStorage = b.cast().unwrap();
    unsafe { bp.Load(&stg).unwrap() };
    let inner: &Graph = unsafe { AsImpl::<Graph>::as_impl(&b) };
    assert_eq!(inner.s.borrow().data, data);
    assert_eq!((inner.s.borrow().pic.width, inner.s.borrow().pic.height), (40, 30));
    assert_eq!(unsafe { ReadClassStg(&stg) }.unwrap(), CLSID);
    let size = unsafe { b.GetExtent(DVASPECT_CONTENT) }.unwrap();
    assert_eq!((size.cx, size.cy), (8000, 6000), "80 × 60 mm in hundredths of a millimetre");
}

#[test]
fn every_picture_format_is_ready() {
    init();
    let d: IDataObject = graph(b"{}").cast().unwrap();
    for f in formats() {
        let mut m = unsafe { d.GetData(&f) }.unwrap_or_else(|e| panic!("format {}: {e}", f.cfFormat));
        if f.cfFormat == CF_ENHMETAFILE.0 {
            let n = unsafe { GetEnhMetaFileBits(m.u.hEnhMetaFile, None) };
            assert!(n > 200, "the metafile holds the picture ({n} bytes)");
        }
        unsafe { ReleaseStgMedium(&mut m) };
    }
}

#[test]
fn pasting_makes_an_embedded_object_that_draws_and_reloads() {
    init();
    register(&std::env::current_exe().unwrap()).unwrap();
    let src: IDataObject = graph(br#"{"name":"P"}"#).cast().unwrap();
    let stg = storage();
    // As a document's Paste does: the object comes from the clipboard data, its picture from the cache.
    let obj: IOleObject = unsafe {
        let mut p = std::ptr::null_mut();
        OleCreateFromData(&src, &IOleObject::IID, OLERENDER_DRAW, std::ptr::null(), None, &stg, &mut p).unwrap();
        IOleObject::from_raw(p)
    };
    unsafe {
        let frame = RECT { left: 0, top: 0, right: 8000, bottom: 6000 };
        let hdc = CreateEnhMetaFileW(None, PCWSTR::null(), Some(&frame as *const RECT), PCWSTR::null());
        OleDraw(&obj, DVASPECT_CONTENT.0, hdc, &RECT { left: 0, top: 0, right: 300, bottom: 225 }).unwrap();
        let _ = DeleteEnhMetaFile(Some(CloseEnhMetaFile(hdc)));
        let ps: IPersistStorage = obj.cast().unwrap();
        OleSave(&ps, &stg, true).unwrap();
        let _ = ps.SaveCompleted(None);
        assert_eq!(ReadClassStg(&stg).unwrap(), CLSID, "the document stores a Datum Plot Graph");
        assert_eq!(read_stream(&stg, DATA).unwrap(), br#"{"name":"P"}"#, "with the graph's project inside");
        let _ = obj.Close(OLECLOSE_NOSAVE);
        drop(obj);
        let mut p = std::ptr::null_mut();
        OleLoad(&stg, &IOleObject::IID, None, &mut p).unwrap();
        let again = IOleObject::from_raw(p);
        assert_eq!(again.GetUserClassID().unwrap(), CLSID, "and opens it again from the saved document");
    }
    unregister();
}

#[test]
fn copy_embedded_offers_the_object_first() {
    init();
    if copy_embedded(b"{}", &picture()).is_err() {
        eprintln!("no clipboard on this machine: skipped");
        return;
    }
    let clip = unsafe { OleGetClipboard() }.unwrap();
    let first = unsafe {
        let e = clip.EnumFormatEtc(DATADIR_GET.0 as u32).unwrap();
        let mut f = [FORMATETC::default()];
        let _ = e.Next(&mut f, None);
        f[0].cfFormat
    };
    assert_eq!(first, cf(w!("Embed Source")));
}
