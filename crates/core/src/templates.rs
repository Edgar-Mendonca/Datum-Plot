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
        sets: sets.iter().map(|(n, _)| DataSet { title: (*n).into(), entry: Entry::Replicates, reps, ..Default::default() }).collect(), cols, ..Default::default()
    };
    t.normalize();
    t
}

pub fn list() -> Vec<Tpl> {
    let dots = |id: &str| {
        let p = build(Some(id)).unwrap();
        let t = &p.tables[0];
        let (xc, yc) = if t.kind == "multi" { (1, t.width() - 1) } else { (0, 1) };
        if t.kind == "survival" {
            let tmax = (0..t.rows).filter_map(|r| t.get(r, 0)).fold(1e-9f64, f64::max);
            let mut pts: Vec<(f64, f64)> = (0..t.rows).filter_map(|r| Some((t.get(r, 0)?, t.get(r, 1)?))).collect();
            pts.sort_by(|a, b| a.0.total_cmp(&b.0));
            let (mut s, mut out, n) = (1.0, vec![(0.0, 1.0)], pts.len());
            for (i, (x, e)) in pts.iter().enumerate() {
                if *e == 1.0 { s *= 1.0 - 1.0 / (n - i) as f64; }
                out.push((x / tmax, s));
            }
            return out;
        }
        if t.kind == "matrix" {
            let mid = t.sets.len() / 2;
            let v: Vec<f64> = (0..t.rows).filter_map(|r| t.get(r, 1 + mid)).collect();
            let (lo, hi) = v.iter().fold((f64::MAX, f64::MIN), |a, &b| (a.0.min(b), a.1.max(b)));
            return v.iter().enumerate().map(|(i, &z)| (i as f64 / (v.len() - 1).max(1) as f64, (z - lo) / (hi - lo).max(1e-9))).collect();
        }
        if t.kind != "xy" && t.kind != "multi" {
            let means: Vec<f64> = t.spans().iter().map(|&(c, _)| { let v: Vec<f64> = (0..t.rows).filter_map(|r| t.get(r, c)).collect(); v.iter().sum::<f64>() / v.len().max(1) as f64 }).collect();
            let top = means.iter().fold(0f64, |a, b| a.max(*b));
            return means.iter().enumerate().map(|(i, m)| (i as f64 / (means.len() - 1).max(1) as f64, m / top.max(1e-9))).collect();
        }
        let pts: Vec<(f64, f64)> = (0..t.rows).filter_map(|r| { let x = t.get(r, xc)?; let ys: Vec<f64> = (yc..yc + t.sets[0].width()).filter_map(|c| t.get(r, c)).collect(); (!ys.is_empty()).then(|| (x, ys[0])) }).collect();
        let log = p.graphs[0].settings.x.scale == "log";
        let fx = |x: f64| if log { x.log10() } else { x };
        let (x0, x1) = pts.iter().fold((f64::MAX, f64::MIN), |a, p| (a.0.min(fx(p.0)), a.1.max(fx(p.0))));
        let (y0, y1) = pts.iter().fold((f64::MAX, f64::MIN), |a, p| (a.0.min(p.1), a.1.max(p.1)));
        let y0 = if y1 > 0.0 { y0.min(0.0) } else { y0 };
        pts.iter().map(|p| ((fx(p.0) - x0) / (x1 - x0).max(1e-9), (p.1 - y0) / (y1 - y0).max(1e-9))).collect()
    };
    vec![
        Tpl { id: "growth", name: "Growth curve", desc: "Optical density over time, two strains in triplicate.", dots: dots("growth") },
        Tpl { id: "standard", name: "Standard curve", desc: "Absorbance of standards entered as mean, SD and N.", dots: dots("standard") },
        Tpl { id: "dose", name: "Dose-response", desc: "Response to two compounds on a log concentration axis.", dots: dots("dose") },
        Tpl { id: "modulus", name: "Tensile test", desc: "Stress–strain of two alloys; the modulus is a linear fit of the elastic region.", dots: dots("modulus") },
        Tpl { id: "arrhenius", name: "Arrhenius", desc: "Rate constants at six temperatures; the analysis gives the activation energy.", dots: dots("arrhenius") },
        Tpl { id: "groups", name: "Compare groups", desc: "Yield strength after three heat treatments: one-way ANOVA with Tukey's test.", dots: dots("groups") },
        Tpl { id: "weibull", name: "Weibull strength", desc: "Fracture strength of two ceramics, 20 bars each: Weibull modulus and characteristic strength.", dots: dots("weibull") },
        Tpl { id: "twoway", name: "Two factors", desc: "Strength of three alloys as received and aged: two-way ANOVA with grouped bars.", dots: dots("twoway") },
        Tpl { id: "counts", name: "Pass or fail", desc: "Specimens that passed or failed inspection with two coating processes: Fisher's exact test and relative risk.", dots: dots("counts") },
        Tpl { id: "phases", name: "Phase fractions", desc: "Point counts of the phases in annealed and quenched steel: pie charts and fractions with 95% CIs.", dots: dots("phases") },
        Tpl { id: "hardness", name: "Many variables", desc: "Hardness of 24 steels from their carbon content and tempering temperature: multiple regression.", dots: dots("hardness") },
        Tpl { id: "corrosion", name: "Time to failure", desc: "Hours to failure of coated and bare specimens in a salt-spray test stopped at 1000 h: Kaplan-Meier curves and the log-rank test.", dots: dots("corrosion") },
        Tpl { id: "batches", name: "Batches", desc: "Strength of specimens from three batches of each of three suppliers: a nested one-way ANOVA with batches as subgroups.", dots: dots("batches") },
        Tpl { id: "spectrum", name: "Spectrum peaks", desc: "A Raman-like spectrum with three overlapping bands on a curved background: peak positions, widths and areas from a Gaussian fit.", dots: dots("spectrum") },
        Tpl { id: "worksheet", name: "Worksheet", desc: "Cooling of a sample: time, temperature and its SD in free columns, with a formula column giving kelvin.", dots: dots("worksheet") },
        Tpl { id: "hardmap", name: "Hardness map", desc: "Hardness measured on a grid across a weld: a contour map, a 3D surface and a 2D Gaussian surface fit.", dots: dots("hardmap") },
        Tpl { id: "dsc", name: "DSC peak", desc: "A melting peak on a sloping baseline: onset and peak temperatures, and the enthalpy from the area.", dots: dots("dsc") },
        Tpl { id: "tga", name: "TGA steps", desc: "Mass loss of a filled polymer in two steps: onsets, the temperatures of fastest loss and the residue.", dots: dots("tga") },
        Tpl { id: "fatigue", name: "S–N curve", desc: "Stress against cycles to failure for an aluminium alloy, with run-outs: a Basquin fit and the fatigue strength at 10⁷ cycles.", dots: dots("fatigue") },
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
            t.sets = vec![DataSet { title: "BSA standard".into(), entry: Entry::MeanSdN, reps: 3, ..Default::default() }];
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
        Some("modulus") => {
            let xs: Vec<f64> = (0..=14).map(|i| i as f64 / 1000.0).collect();
            // Elastic up to ~0.4 % strain, then work hardening (stress in MPa).
            let curve = |e_mod: f64, ys: f64| move |e: f64| if e <= ys / e_mod { e_mod * e } else { ys + 0.25 * e_mod * (e - ys / e_mod).powf(0.6) * 0.08 };
            let (a, b) = (curve(205_000.0, 760.0), curve(70_000.0, 270.0));
            let t = table(["Tensile", "Strain", "", "Stress", "MPa"], &xs, &[("Steel", &a), ("Aluminium", &b)], 2, 0.012, 1);
            p.name = "Tensile test".into();
            p.info = Info { title: "Tensile test".into(), experiment: "Engineering stress against strain for a steel and an aluminium alloy, two specimens each. The elastic modulus is the slope of a straight line fitted from 0 to 0.003 strain (here in MPa; divide by 1000 for GPa).".into(), ..Default::default() };
            let id = p.add_table(t, Some(GraphSettings { line: false, ..g }));
            let aid = p.take_id();
            p.analyses.push(Analysis { id: aid, table: id, name: "Elastic modulus".into(), kind: "linear".into(), sets: vec![],
                options: serde_json::json!({ "model": "line", "xmin": 0, "xmax": 0.003, "points": "each", "compare": true, "bands": "ci", "label": true }) });
            p.graphs.last_mut().unwrap().settings.overlays.push(aid);
            let tid = p.take_id();
            p.analyses.push(Analysis { id: tid, table: id, name: "Tensile properties".into(), kind: "tensile".into(), sets: vec![], options: serde_json::json!({ "strain": "abs", "offset": 0.2 }) });
        }
        Some("groups") => {
            let mut seed = 5u64;
            let groups = [("As cast", 212.0, 14.0), ("T4 (solution treated)", 236.0, 12.0), ("T6 (aged)", 268.0, 15.0)];
            let mut t = Table::column(3);
            t.name = "Heat treatment".into();
            t.y_title = "Yield strength".into();
            t.y_units = "MPa".into();
            for (k, (name, mean, sd)) in groups.iter().enumerate() {
                t.sets[k].title = (*name).into();
                t.cols[k + 1] = (0..t.rows).map(|r| (r < 8).then(|| round(mean + jitter(&mut seed, sd * 1.7), 1))).collect();
            }
            p.name = "Compare groups".into();
            p.info = Info { title: "Heat treatment".into(), experiment: "Yield strength of an aluminium alloy as cast, after solution treatment (T4) and after ageing (T6), eight tensile specimens each. One-way ANOVA with Tukey's multiple comparisons; the stars on the graph come from the analysis.".into(), ..Default::default() };
            let id = p.add_table(t, Some(GraphSettings { column: "scatter".into(), points: "each".into(), ..g }));
            let aid = p.take_id();
            p.analyses.push(Analysis { id: aid, table: id, name: "One-way ANOVA".into(), kind: "anova".into(), sets: vec![], options: serde_json::json!({ "anova": "ordinary", "posthoc": "tukey", "brackets": "sig" }) });
            p.graphs.last_mut().unwrap().settings.overlays.push(aid);
        }
        Some("twoway") => {
            let mut seed = 13u64;
            let mut t = Table::grouped(3, 2);
            t.name = "Alloys".into();
            t.y_title = "Yield strength".into();
            t.y_units = "MPa".into();
            t.row_titles = vec!["6061".into(), "7075".into(), "2024".into()];
            t.normalize();
            let base = [[150.0, 276.0], [210.0, 503.0], [175.0, 345.0]];
            for (k, name) in ["As received", "Aged (T6)"].iter().enumerate() {
                t.sets[k].title = (*name).into();
                for j in 0..3 {
                    t.cols[1 + 3 * k + j] = (0..t.rows).map(|r| base.get(r).map(|b| round(b[k] * (1.0 + jitter(&mut seed, 0.04)), 0))).collect();
                }
            }
            p.name = "Two factors".into();
            p.info = Info { title: "Alloy and heat treatment".into(), experiment: "Yield strength of three aluminium alloys as received and after ageing, three specimens each. Two-way ANOVA: does ageing help, does the alloy matter, and does ageing help every alloy equally (interaction)? Šidák comparisons within each alloy give the stars.".into(), ..Default::default() };
            let id = p.add_table(t, Some(GraphSettings { column: "bars".into(), points: "each".into(), legend: Legend { show: true, loc: "upper left".into() }, ..g }));
            let aid = p.take_id();
            p.analyses.push(Analysis { id: aid, table: id, name: "Two-way ANOVA".into(), kind: "twoway".into(), sets: vec![], options: serde_json::json!({ "posthoc": "sidak", "compare": "rows", "rowname": "Alloy", "colname": "Treatment", "brackets": "sig" }) });
            p.graphs.last_mut().unwrap().settings.overlays.push(aid);
        }
        Some("counts") => {
            let mut t = Table::contingency(2, 2);
            t.name = "Inspection".into();
            t.row_titles = vec!["Old coating".into(), "New coating".into()];
            t.sets[0].title = "Failed".into();
            t.sets[1].title = "Passed".into();
            t.normalize();
            t.cols[1] = vec![Some(14.0), Some(5.0), None];
            t.cols[2] = vec![Some(36.0), Some(45.0), None];
            t.normalize();
            p.name = "Pass or fail".into();
            p.info = Info { title: "Coating inspection".into(), experiment: "50 specimens coated with each process were inspected for cracks. Fisher's exact test asks whether the failure rate differs; the relative risk says by how much.".into(), ..Default::default() };
            let id = p.add_table(t, Some(GraphSettings { column: "percent".into(), points: "mean".into(), error: "none".into(), ..g }));
            let aid = p.take_id();
            p.analyses.push(Analysis { id: aid, table: id, name: "Fisher's exact test".into(), kind: "contingency".into(), sets: vec![], options: serde_json::json!({}) });
        }
        Some("phases") => {
            let mut t = Table::parts(4, 2);
            t.name = "Phases".into();
            t.y_title = "Points counted".into();
            t.row_titles = vec!["Ferrite".into(), "Pearlite".into(), "Martensite".into(), "Retained austenite".into()];
            t.sets[0].title = "Annealed".into();
            t.sets[1].title = "Quenched".into();
            t.cols[1] = vec![Some(610.0), Some(390.0), Some(0.0), Some(0.0)];
            t.cols[2] = vec![Some(35.0), Some(0.0), Some(885.0), Some(80.0)];
            t.normalize();
            p.name = "Phase fractions".into();
            p.info = Info { title: "Phase fractions".into(), experiment: "Point counting (1000 grid points) on micrographs of a steel annealed and quenched. Fractions of total give each phase's share with a 95% confidence interval.".into(), ..Default::default() };
            let id = p.add_table(t, Some(GraphSettings { column: "pie".into(), points: "mean".into(), error: "none".into(), ..g }));
            let aid = p.take_id();
            p.analyses.push(Analysis { id: aid, table: id, name: "Fractions of total".into(), kind: "parts".into(), sets: vec![], options: serde_json::json!({}) });
        }
        Some("hardness") => {
            let mut seed = 5u64;
            let mut t = Table::multi(3, 24);
            t.name = "Steels".into();
            for (k, n) in ["Carbon", "Tempering", "Hardness"].iter().enumerate() {
                t.sets[k].title = (*n).into();
            }
            for r in 0..24 {
                let (c, temp) = (0.2 + 0.1 * (r % 6) as f64, 200.0 + 100.0 * (r / 6) as f64);
                t.row_titles[r] = format!("S{}", r + 1);
                t.cols[1][r] = Some(round(c + jitter(&mut seed, 0.01), 3));
                t.cols[2][r] = Some(temp);
                t.cols[3][r] = Some(round(330.0 + 520.0 * c - 0.55 * temp + jitter(&mut seed, 18.0), 0));
            }
            t.y_title = "Hardness".into();
            t.y_units = "HV".into();
            p.name = "Many variables".into();
            p.info = Info { title: "Hardness of tempered steels".into(), experiment: "Vickers hardness of 24 quenched steels with six carbon contents (wt%), tempered at four temperatures (°C). Multiple regression gives the effect of each on the hardness, holding the other constant.".into(), ..Default::default() };
            let id = p.add_table(t, Some(GraphSettings { points: "each".into(), sets: vec![SetStyle::default(), SetStyle { show: false, ..Default::default() }], ..g }));
            let aid = p.take_id();
            p.analyses.push(Analysis { id: aid, table: id, name: "Multiple regression".into(), kind: "multireg".into(), sets: vec![], options: serde_json::json!({ "y": 2, "model": "linear" }) });
        }
        Some("corrosion") => {
            let mut seed = 11u64;
            let mut t = Table::survival(2);
            t.name = "Failures".into();
            t.x_title = "Time".into();
            t.x_units = "h".into();
            t.rows = 28;
            t.normalize();
            for (k, (name, scale)) in [("Bare", 380.0), ("Coated", 900.0)].iter().enumerate() {
                t.sets[k].title = (*name).into();
                for i in 0..14 {
                    let u: f64 = 0.5 + jitter(&mut seed, 0.48);
                    let h = round(scale * (-(1.0 - u).ln()).powf(1.0 / 1.8), 0);
                    let r = k * 14 + i;
                    t.cols[0][r] = Some(h.min(1000.0));
                    t.cols[k + 1][r] = Some(if h < 1000.0 { 1.0 } else { 0.0 });
                }
            }
            p.name = "Time to failure".into();
            p.info = Info { title: "Salt-spray corrosion".into(), experiment: "Hours until the first pit on 14 bare and 14 coated steel specimens in a salt-spray cabinet. The test stopped at 1000 h, so specimens still intact then are censored (0). Kaplan-Meier curves and the log-rank test compare the two.".into(), ..Default::default() };
            let id = p.add_table(t, Some(GraphSettings { error: "none".into(), ..g }));
            let aid = p.take_id();
            p.analyses.push(Analysis { id: aid, table: id, name: "Survival analysis".into(), kind: "survival".into(), sets: vec![], options: serde_json::json!({}) });
        }
        Some("batches") => {
            let mut seed = 21u64;
            let mut t = Table::nested(3, 3);
            t.name = "Specimens".into();
            t.y_title = "Tensile strength".into();
            t.y_units = "MPa".into();
            t.rows = 5;
            t.normalize();
            for (k, (name, mean)) in [("Supplier A", 512.0), ("Supplier B", 548.0), ("Supplier C", 520.0)].iter().enumerate() {
                t.sets[k].title = (*name).into();
                for b in 0..3 {
                    let batch = mean + jitter(&mut seed, 9.0);
                    t.cols[1 + 3 * k + b] = (0..5).map(|_| Some(round(batch + jitter(&mut seed, 6.0), 0))).collect();
                }
            }
            p.name = "Batches".into();
            p.info = Info { title: "Strength by supplier".into(), experiment: "Five specimens from each of three batches from each of three suppliers. Specimens from one batch are not independent, so the nested ANOVA tests the suppliers against the spread between batches.".into(), ..Default::default() };
            let id = p.add_table(t, Some(GraphSettings { error: "sd".into(), ..g }));
            let aid = p.take_id();
            p.analyses.push(Analysis { id: aid, table: id, name: "Nested ANOVA".into(), kind: "nested".into(), sets: vec![], options: serde_json::json!({}) });
        }
        Some("weibull") => {
            let mut seed = 3u64;
            let mut t = Table::column(2);
            t.name = "Fracture strength".into();
            t.y_title = "Flexural strength".into();
            t.y_units = "MPa".into();
            t.rows = 20;
            t.normalize();
            for (k, (name, s0, m)) in [("Alumina", 380.0, 11.0), ("Zirconia", 910.0, 16.0)].iter().enumerate() {
                t.sets[k].title = (*name).into();
                t.cols[k + 1] = (0..20).map(|_| { let u: f64 = 0.5 + jitter(&mut seed, 0.49); Some(round(s0 * (-(1.0 - u).ln()).powf(1.0 / m), 0)) }).collect();
            }
            p.name = "Weibull strength".into();
            p.info = Info { title: "Weibull analysis".into(), experiment: "Four-point bending strength of alumina and zirconia bars, 20 each. The Weibull analysis gives the Weibull modulus m (scatter: higher is more reliable) and the characteristic strength σ0 (63.2 % fail below it).".into(), ..Default::default() };
            let id = p.add_table(t, Some(GraphSettings { column: "box".into(), points: "each".into(), ..g }));
            let aid = p.take_id();
            p.analyses.push(Analysis { id: aid, table: id, name: "Weibull analysis".into(), kind: "weibull".into(), sets: vec![], options: serde_json::json!({ "method": "mle" }) });
        }
        Some("spectrum") => {
            let xs: Vec<f64> = (0..=300).map(|i| 200.0 + 2.0 * i as f64).collect();
            let band = |x: f64, a: f64, c: f64, w: f64| a * (-((x - c) / w).powi(2) / 2.0).exp();
            let mut seed = 17u64;
            let mut t = Table { name: "Spectrum".into(), x_title: "Raman shift".into(), x_units: "cm⁻¹".into(), y_title: "Intensity".into(), y_units: "counts".into(), rows: xs.len(),
                sets: vec![DataSet { title: "Sample".into(), entry: Entry::Replicates, reps: 1, ..Default::default() }], ..Default::default() };
            let f = |x: f64| 120.0 + 0.00012 * (x - 200.0).powi(2) + band(x, 900.0, 420.0, 9.0) + band(x, 520.0, 470.0, 14.0) + band(x, 640.0, 640.0, 11.0);
            t.cols = vec![xs.iter().map(|&v| Some(v)).collect(), xs.iter().map(|&v| Some(round(f(v) + jitter(&mut seed, 12.0), 0))).collect()];
            t.normalize();
            p.name = "Spectrum peaks".into();
            p.info = Info { title: "Raman bands".into(), experiment: "A spectrum with three bands on a curved fluorescence background. Peak analysis removes a polynomial baseline, finds the bands and fits them as Gaussians: position, width and area of each.".into(), ..Default::default() };
            let id = p.add_table(t, Some(GraphSettings { line: true, points: "mean".into(), error: "none".into(), y: Axis { auto: true, ..Axis::default() }, sets: vec![SetStyle { symbol: "none".into(), width: 1.0, ..Default::default() }], ..g }));
            let aid = p.take_id();
            p.analyses.push(Analysis { id: aid, table: id, name: "Peak analysis".into(), kind: "peaks".into(), sets: vec![], options: serde_json::json!({ "baseline": "poly", "order": 2, "fit": "gauss" }) });
            p.graphs.last_mut().unwrap().settings.overlays.push(aid);
        }
        Some("worksheet") => {
            let mut seed = 23u64;
            let mut t = Table::sheet(4);
            t.name = "Cooling".into();
            for (k, (title, role, units)) in [("Time", "x", "min"), ("Temperature", "", "°C"), ("SD", "yerr", "°C"), ("Temperature (K)", "skip", "K")].iter().enumerate() {
                t.sets[k] = DataSet { title: (*title).into(), role: (*role).into(), units: (*units).into(), reps: 1, ..Default::default() };
            }
            t.sets[1].comment = "Mean of three thermocouples".into();
            t.sets[3].formula = "B + 273.15".into();
            t.rows = 13;
            t.normalize();
            for r in 0..13 {
                let (m, temp) = (5.0 * r as f64, 22.0 + 180.0 * (-(5.0 * r as f64) / 14.0).exp());
                let v = round(temp + jitter(&mut seed, 1.5), 1);
                t.cols[1][r] = Some(m);
                t.cols[2][r] = Some(v);
                t.cols[3][r] = Some(round(1.2 + jitter(&mut seed, 0.6), 1));
                t.cols[4][r] = Some(round(v + 273.15, 2));
            }
            p.name = "Worksheet".into();
            p.info = Info { title: "Cooling curve".into(), experiment: "A hot sample cooling in air. In a worksheet each column has a role: Time is X, Temperature is Y with its SD as the error, and Temperature (K) is a formula column (B + 273.15) that is not plotted.".into(), ..Default::default() };
            p.add_table(t, Some(GraphSettings { line: true, error: "sd".into(), ..g }));
        }
        Some("hardmap") => {
            let mut seed = 29u64;
            let mut t = Table::matrix(21, 9);
            t.name = "Hardness map".into();
            t.x_title = "Distance across the weld".into();
            t.x_units = "mm".into();
            t.y_title = "Hardness".into();
            t.y_units = "HV".into();
            for (k, s) in t.sets.iter_mut().enumerate() {
                s.title = format!("{}", k as f64 * 1.5);
            }
            for r in 0..21 {
                let x = -10.0 + r as f64;
                t.cols[0][r] = Some(x);
                for k in 0..9 {
                    let y = k as f64 * 1.5;
                    t.cols[k + 1][r] = Some(round(210.0 + 95.0 * (-(x * x) / (2.0 * 3.2 * 3.2) - (y - 4.0).powi(2) / (2.0 * 4.5 * 4.5)).exp() + jitter(&mut seed, 4.0), 0));
                }
            }
            p.name = "Hardness map".into();
            p.info = Info { title: "Hardness across a weld".into(), experiment: "Vickers hardness on a 21 × 9 grid across a weld bead (X: distance from the weld centre line, Y: depth below the surface). The contour map shows the hard zone; a 2D Gaussian surface fit gives its centre, peak hardness and width.".into(), ..Default::default() };
            let id = p.add_table(t, Some(GraphSettings { column: "contour".into(), palette: "viridis".into(), width: 100.0, y: Axis { title: "Depth (mm)".into(), ..Axis::default() }, ..g }));
            let aid = p.take_id();
            p.analyses.push(Analysis { id: aid, table: id, name: "Surface fit".into(), kind: "surface".into(), sets: vec![], options: serde_json::json!({ "model": "gauss" }) });
            p.graphs.last_mut().unwrap().settings.overlays.push(aid);
        }
        Some("dsc") => {
            let xs: Vec<f64> = (0..=120).map(|i| 140.0 + 0.5 * i as f64).collect();
            let peak = |t: f64| -0.35 - 0.004 * (t - 140.0) - 2.4 * (-((t - 167.0) / 3.2).powi(2)).exp();
            let mut seed = 9u64;
            let mut t = Table { name: "DSC".into(), x_title: "Temperature".into(), x_units: "°C".into(), y_title: "Heat flow".into(), y_units: "W/g".into(), rows: xs.len(),
                sets: vec![DataSet { title: "Polymer melt".into(), entry: Entry::Replicates, reps: 1, ..Default::default() }], ..Default::default() };
            t.cols = vec![xs.iter().map(|&v| Some(v)).collect(), xs.iter().map(|&v| Some(round(peak(v) + jitter(&mut seed, 0.012), 4))).collect()];
            t.normalize();
            p.name = "DSC peak".into();
            p.info = Info { title: "DSC melting peak".into(), experiment: "Heat flow of a semicrystalline polymer heated at 10 K/min (endotherm down). Thermal analysis gives the extrapolated onset and the peak temperature, and the melting enthalpy: the area between the curve and a straight baseline divided by the heating rate (J/g).".into(), ..Default::default() };
            let id = p.add_table(t, Some(GraphSettings { line: true, points: "mean".into(), error: "none".into(), sets: vec![SetStyle { symbol: "none".into(), width: 1.4, ..Default::default() }], ..g }));
            let aid = p.take_id();
            p.analyses.push(Analysis { id: aid, table: id, name: "Thermal analysis".into(), kind: "thermal".into(), sets: vec![], options: serde_json::json!({ "mode": "dsc", "rate": 10, "direction": "down" }) });
            p.graphs.last_mut().unwrap().settings.overlays.push(aid);
        }
        Some("tga") => {
            let xs: Vec<f64> = (0..=250).map(|i| 50.0 + 2.5 * i as f64).collect();
            let step = |t: f64, c: f64, w: f64| 1.0 / (1.0 + (-(t - c) / w).exp());
            let mut seed = 13u64;
            let mut t = Table { name: "TGA".into(), x_title: "Temperature".into(), x_units: "°C".into(), y_title: "Mass".into(), y_units: "mg".into(), rows: xs.len(),
                sets: vec![DataSet { title: "Filled polymer".into(), entry: Entry::Replicates, reps: 1, ..Default::default() }], ..Default::default() };
            t.cols = vec![xs.iter().map(|&v| Some(v)).collect(), xs.iter().map(|&v| Some(round(12.0 * (1.0 - 0.08 * step(v, 260.0, 9.0) - 0.55 * step(v, 445.0, 12.0)) + jitter(&mut seed, 0.004), 4))).collect()];
            t.normalize();
            p.name = "TGA steps".into();
            p.info = Info { title: "TGA of a filled polymer".into(), experiment: "Mass of a 12 mg sample heated at 10 K/min in nitrogen: moisture and additives leave first, then the polymer decomposes; the filler stays as residue. Thermal analysis (TGA) gives each step's onset, the temperature of fastest loss and the mass lost.".into(), ..Default::default() };
            let id = p.add_table(t, Some(GraphSettings { line: true, points: "mean".into(), error: "none".into(), y: Axis { auto: true, ..Axis::default() }, sets: vec![SetStyle { symbol: "none".into(), width: 1.4, ..Default::default() }], ..g }));
            let aid = p.take_id();
            p.analyses.push(Analysis { id: aid, table: id, name: "Thermal analysis".into(), kind: "thermal".into(), sets: vec![], options: serde_json::json!({ "mode": "tga" }) });
            p.graphs.last_mut().unwrap().settings.overlays.push(aid);
        }
        Some("fatigue") => {
            let mut seed = 19u64;
            let n = [2.0e4, 4.5e4, 8.0e4, 1.5e5, 3.2e5, 6.0e5, 1.1e6, 2.4e6, 5.0e6, 1.0e7, 1.0e7];
            let mut t = Table { name: "Fatigue".into(), x_title: "Cycles to failure".into(), y_title: "Stress amplitude".into(), y_units: "MPa".into(), rows: n.len(),
                sets: vec![DataSet { title: "7075-T6".into(), entry: Entry::Replicates, reps: 1, ..Default::default() }], ..Default::default() };
            t.cols = vec![n.iter().map(|&v| Some(v)).collect(), n.iter().enumerate().map(|(i, &v)| Some(round(if i >= 9 { 158.0 + 4.0 * (i - 9) as f64 } else { 1060.0 * v.powf(-0.122) * (1.0 + jitter(&mut seed, 0.03)) }, 0))).collect()];
            t.normalize();
            p.name = "S–N curve".into();
            p.info = Info { title: "Fatigue of 7075-T6".into(), experiment: "Fully reversed stress amplitude against cycles to failure. Two specimens did not fail by 10⁷ cycles (run-outs). The Basquin fit gives the fatigue strength at any life.".into(), ..Default::default() };
            let id = p.add_table(t, Some(GraphSettings { points: "each".into(), line: false, x: Axis { scale: "log".into(), ..Axis::default() }, ..g }));
            let aid = p.take_id();
            p.analyses.push(Analysis { id: aid, table: id, name: "S–N curve".into(), kind: "sn".into(), sets: vec![], options: serde_json::json!({ "runout": 1.0e7, "at": "1e6, 1e7" }) });
            p.graphs.last_mut().unwrap().settings.overlays.push(aid);
        }
        Some("arrhenius") => {
            let xs = [300.0, 325.0, 350.0, 375.0, 400.0, 425.0];
            let k = |ea: f64, a: f64| move |c: f64| a * (-ea / (8.314462618 * (c + 273.15))).exp();
            let (x, y) = (k(62_000.0, 4.0e7), k(85_000.0, 6.0e9));
            let t = table(["Rates", "Temperature", "°C", "Rate constant k", "1/s"], &xs, &[("Catalyst A", &x), ("Catalyst B", &y)], 3, 0.05, 6);
            p.name = "Arrhenius".into();
            p.info = Info { title: "Activation energy".into(), experiment: "Rate constants of a reaction on two catalysts at six temperatures, three runs each. The Arrhenius analysis fits ln(k) against 1/T.".into(), ..Default::default() };
            let id = p.add_table(t, Some(GraphSettings { line: false, y: Axis { scale: "log".into(), ..Axis::default() }, ..g }));
            let aid = p.take_id();
            p.analyses.push(Analysis { id: aid, table: id, name: "Activation energy".into(), kind: "arrhenius".into(), sets: vec![],
                options: serde_json::json!({ "tunit": "C", "eunit": "kJ/mol", "points": "each", "label": true }) });
            p.graphs.last_mut().unwrap().settings.overlays.push(aid);
        }
        _ => return None,
    }
    p.normalize();
    Some(p)
}
