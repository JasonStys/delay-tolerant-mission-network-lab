//! Bounded stdin-only native worker by Jason Stys; main/input/output variables: docs/CODE_INDEX.md.
//! Complete parse/restore must succeed before any stdout evidence. No shell, sockets or caller paths.
use delay_tolerant_mission_network_lab::{Case, State, unhex};
use std::io::{self, Read};

/// Read a finite envelope, construct or restore state, advance, then emit one fixed-contract JSON result.
fn run() -> Result<(), &'static str> {
    if std::env::args().len() != 1 {
        return Err("no arguments accepted");
    }
    let mut bytes = Vec::new();
    io::stdin()
        .take(16_385)
        .read_to_end(&mut bytes)
        .map_err(|_| "stdin")?;
    let text = std::str::from_utf8(&bytes).map_err(|_| "encoding")?;
    let (case, checkpoint) = Case::parse(text)?;
    let mut state = if let Some(hex) = checkpoint {
        State::restore(&case, &unhex(&hex, 1024)?)?
    } else {
        State::new(&case)
    };
    if case.pause != 0 && case.pause < state.next {
        return Err("pause precedes checkpoint");
    }
    let (events, samples) = state.advance(&case);
    println!("{}", state.json(&case, &events, &samples));
    Ok(())
}
/// Controlled worker failures use exit 2 and a constant diagnostic, never partial evidence or payloads.
fn main() {
    if run().is_err() {
        eprintln!("Invalid lab input or checkpoint");
        std::process::exit(2);
    }
}
