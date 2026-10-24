//! Sample projects for the Home page: real-looking data and a ready graph.
use crate::model::*;
use serde::Serialize;

#[derive(Serialize)]
pub struct Tpl {
    pub id: &'static str,
    pub name: &'static str,
    pub desc: &'static str,
    /// Mean points of the first data set (x, y), scaled 0–1, for the tile's picture.
    pub dots: Vec<(f64, f64)>,
}

/// Repeatable "noise" so the samples look like measurements and never change.
fn jitter(seed: &mut u64, size: f64) -> f64 {
    *seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
    ((*seed >> 33) as f64 / (1u64 << 31) as f64 - 0.5) * 2.0 * size
}
fn round(v: f64, d: i32) -> f64 {
    let k = 10f64.powi(d);
    (v * k).round() / k
}

/// A table from X values and, per data set, a model curve with replicate noise.
/// `titles`: table name, X title, X units, Y title, Y units.
fn table(titles: [&str; 5], xs: &[f64], sets: &[(&str, &dyn Fn(f64) -> f64)], reps: usize, noise: f64, digits: i32) -> Table {
    let mut seed = 7u64;
    let mut cols = vec![xs.iter().map(|&v| Some(v)).collect::<Vec<_>>()];
    for (_, f) in sets {
        for _ in 0..reps {
            cols.push(xs.iter().map(|&v| Some(round(f(v) * (1.0 + jitter(&mut seed, noise)), digits))).collect());
        }
    }
    let mut t = Table {
        name: titles[0].into(), x_title: titles[1].into(), x_units: titles[2].into(), y_title: titles[3].into(), y_units: titles[4].into(), rows: xs.len().max(12),
        sets: sets.iter().map(|(n, _)| DataSet { title: (*n).into(), entry: Entry::Replicates, reps }).collect(), cols, ..Default::default()
    };
    t.normalize();
    t
}

pub fn list() -> Vec<Tpl> {
    let dots = |id: &str| {
        let p = build(Some(id)).unwrap();
        let t = &p.tables[0];
        let pts: Vec<(f64, f64)> = (0..t.rows).filter_map(|r| { let x = t.get(r, 0)?; let ys: Vec<f64> = (1..1 + t.sets[0].width()).filter_map(|c| t.get(r, c)).collect(); (!ys.is_empty()).then(|| (x, ys[0])) }).collect();
        let log = p.graphs[0].settings.x.scale == "log";
        let fx = |x: f64| if log { x.log10() } else { x };
        let (x0, x1) = pts.iter().fold((f64::MAX, f64::MIN), |a, p| (a.0.min(fx(p.0)), a.1.max(fx(p.0))));
        let y1 = pts.iter().fold(0f64, |a, p| a.max(p.1));
        pts.iter().map(|p| ((fx(p.0) - x0) / (x1 - x0).max(1e-9), p.1 / y1.max(1e-9))).collect()
    };
    vec![
        Tpl { id: "growth", name: "Growth curve", desc: "Optical density over time, two strains in triplicate.", dots: dots("growth") },
        Tpl { id: "standard", name: "Standard curve", desc: "Absorbance of standards entered as mean, SD and N.", dots: dots("standard") },
        Tpl { id: "dose", name: "Dose-response", desc: "Response to two compounds on a log concentration axis.", dots: dots("dose") },
    ]
}

/// A new project: blank (None) or one of the samples.
pub fn build(id: Option<&str>) -> Option<Project> {
    let mut p = Project::new("Project1");
    let g = GraphSettings::default();
    match id {
        None | Some("xy") => {
            p.add_table(Table::default(), Some(g));
        }
        Some("growth") => {
            let xs: Vec<f64> = (0..=12).map(|h| h as f64 * 2.0).collect();
            let wt = |t: f64| 0.05 + 1.6 / (1.0 + (-(t - 9.0) / 2.0).exp());
            let mu = |t: f64| 0.05 + 1.1 / (1.0 + (-(t - 12.0) / 2.6).exp());
            let t = table(["Growth", "Time", "h", "OD600", ""], &xs, &[("Wild type", &wt), ("Mutant", &mu)], 3, 0.06, 3);
            p.name = "Growth curve".into();
            p.info = Info { title: "Growth curve".into(), experiment: "Growth of wild type and mutant strains in LB at 37 °C, OD600 every 2 hours, three biological replicates.".into(), ..Default::default() };
            p.add_table(t, Some(GraphSettings { error: "sd".into(), ..g }));
        }
        Some("standard") => {
            let xs = [0.0, 5.0, 10.0, 25.0, 50.0, 75.0, 100.0];
            let mut t = Table { name: "Standards".into(), x_title: "Concentration".into(), x_units: "µg/mL".into(), y_title: "Absorbance".into(), y_units: "A562".into(), rows: 12, ..Default::default() };
            t.sets = vec![DataSet { title: "BSA standard".into(), entry: Entry::MeanSdN, reps: 3 }];
            let mut seed = 11u64;
            t.cols = vec![xs.iter().map(|&v| Some(v)).collect(), xs.iter().map(|&c| Some(round(0.095 + 0.0112 * c - 0.000021 * c * c, 3))).collect(),
                xs.iter().map(|_| Some(round(0.012 + jitter(&mut seed, 0.006), 3))).collect(), xs.iter().map(|_| Some(3.0)).collect()];
            t.normalize();
            p.name = "Standard curve".into();
            p.info = Info { title: "BCA protein assay".into(), experiment: "BSA standards read at 562 nm, each in triplicate (entered as mean, SD and N).".into(), ..Default::default() };
            p.add_table(t, Some(GraphSettings { line: false, ..g }));
        }
        Some("dose") => {
            let xs = [0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0, 300.0, 1000.0];
            let hill = |ec: f64, top: f64, h: f64| move |x: f64| 2.0 + (top - 2.0) / (1.0 + (ec / x).powf(h));
            let (a, b) = (hill(8.0, 98.0, 1.1), hill(60.0, 85.0, 0.9));
            let t = table(["Dose-response", "Concentration", "nM", "Response", "% of max"], &xs, &[("Compound A", &a), ("Compound B", &b)], 3, 0.05, 1);
            p.name = "Dose-response".into();
            p.info = Info { title: "Dose-response".into(), experiment: "Response of cells to compounds A and B, nine concentrations in triplicate. Curve fitting arrives in Datum Plot 0.2.".into(), ..Default::default() };
            p.add_table(t, Some(GraphSettings { line: true, x: Axis { scale: "log".into(), ..Axis::default() }, ..g }));
        }
        _ => return None,
    }
    p.normalize();
    Some(p)
}
