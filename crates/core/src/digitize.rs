//! The graph digitizer (E8, 0.4.1): points clicked on a picture of a graph become an XY table. The window sends
//! pixel positions only; the values come from here. Each axis is set by two clicked marks with known values, and
//! a click is projected onto the line through them, so a slightly tilted scan still reads right. Log axes
//! interpolate in powers of ten.
use crate::model::{DataSet, Entry, Table};
use serde::Deserialize;

/// A clicked mark on an axis: where (pixels in the picture) and the value printed there.
#[derive(Debug, Clone, Copy, Deserialize)]
pub struct Mark {
    pub px: f64,
    pub py: f64,
    pub value: f64,
}

/// The two marks of each axis, and whether the axis is logarithmic.
#[derive(Debug, Clone, Deserialize)]
pub struct Calib {
    pub x: [Mark; 2],
    pub y: [Mark; 2],
    #[serde(default)]
    pub xlog: bool,
    #[serde(default)]
    pub ylog: bool,
}

/// One data set's clicked points (pixels).
#[derive(Debug, Clone, Deserialize)]
pub struct Traced {
    pub title: String,
    pub points: Vec<(f64, f64)>,
}

/// The value at pixel `p` along the axis set by marks `a` and `b`.
pub fn value(a: &Mark, b: &Mark, log: bool, p: (f64, f64)) -> Option<f64> {
    let (dx, dy) = (b.px - a.px, b.py - a.py);
    let l2 = dx * dx + dy * dy;
    if l2.is_nan() || l2 <= 1e-9 {
        return None;
    }
    let t = ((p.0 - a.px) * dx + (p.1 - a.py) * dy) / l2;
    let v = if log {
        if !(a.value > 0.0 && b.value > 0.0) {
            return None;
        }
        10f64.powf(a.value.log10() + t * (b.value.log10() - a.value.log10()))
    } else {
        a.value + t * (b.value - a.value)
    };
    v.is_finite().then_some(v)
}

/// Checks the marks: two different places and two different values per axis, positive values on a log axis.
fn check(c: &Calib) -> Result<(), String> {
    for (name, m, log) in [("X", &c.x, c.xlog), ("Y", &c.y, c.ylog)] {
        let far = ((m[1].px - m[0].px).powi(2) + (m[1].py - m[0].py).powi(2)).sqrt();
        if far.is_nan() || far < 5.0 {
            return Err(format!("Click the two {name} marks further apart (they are almost at the same place)."));
        }
        if !(m[0].value.is_finite() && m[1].value.is_finite()) || m[0].value == m[1].value {
            return Err(format!("Type two different values for the {name} marks."));
        }
        if log && !(m[0].value > 0.0 && m[1].value > 0.0) {
            return Err(format!("A logarithmic {name} axis needs marks above zero."));
        }
    }
    Ok(())
}

/// The table: one row per point, X first, each data set in its own column (sorted by X within the set).
pub fn table(name: &str, c: &Calib, sets: &[Traced]) -> Result<Table, String> {
    check(c)?;
    let sets: Vec<&Traced> = sets.iter().filter(|s| !s.points.is_empty()).collect();
    if sets.is_empty() {
        return Err("Click some points on the graph first.".into());
    }
    let n: usize = sets.iter().map(|s| s.points.len()).sum();
    if n > 100_000 {
        return Err("Too many points.".into());
    }
    let mut cols = vec![vec![None; n]; sets.len() + 1];
    let mut r = 0;
    for (k, s) in sets.iter().enumerate() {
        let mut pts: Vec<(f64, f64)> =
            s.points.iter().filter_map(|&p| Some((value(&c.x[0], &c.x[1], c.xlog, p)?, value(&c.y[0], &c.y[1], c.ylog, p)?))).collect();
        pts.sort_by(|a, b| a.0.total_cmp(&b.0));
        for (x, y) in pts {
            cols[0][r] = Some(x);
            cols[k + 1][r] = Some(y);
            r += 1;
        }
    }
    let mut t = Table {
        name: if name.trim().is_empty() { "Digitized".into() } else { name.trim().chars().take(120).collect() },
        rows: r.max(1),
        sets: sets.iter().map(|s| DataSet { title: s.title.trim().chars().take(120).collect(), entry: Entry::Replicates, reps: 1, ..Default::default() }).collect(),
        cols: cols.into_iter().map(|mut c| {
            c.truncate(r.max(1));
            c
        }).collect(),
        ..Default::default()
    };
    t.normalize();
    Ok(t)
}
