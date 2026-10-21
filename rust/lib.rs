//! Bounded deterministic store-and-forward engine by Jason Stys.
//! Types/functions/fields are indexed in docs/CODE_INDEX.md. No unsafe, sockets or external crates.
//! This invented three-node lab profile is not BPv7, a convergence layer or a spacecraft interface.

use std::fmt::Write;

/// Source message with immutable original payload and release-relative expiry in integer lab ticks.
#[derive(Clone, Debug)]
pub struct Message {
    pub id: u16,
    pub release: u16,
    pub ttl: u16,
    pub payload: Vec<u8>,
}
/// One directed half-open departure window on hop 0 (probe-relay) or 1 (relay-ground).
#[derive(Clone, Debug)]
pub struct Contact {
    pub hop: u8,
    pub start: u16,
    pub end: u16,
}
/// Validated bounded input; pause is an exclusive processing boundary, not fingerprint content.
#[derive(Clone, Debug)]
pub struct Case {
    pub horizon: u16,
    pub capacity: u16,
    pub delay: u16,
    pub policy: u8,
    pub fault: u8,
    pub pause: u16,
    pub messages: Vec<Message>,
    pub contacts: Vec<Contact>,
}
/// Durable progress: status 0 unreleased, 1 retained, 2 delivered, 3 expired, 4 rejected at source.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Progress {
    pub status: u8,
    pub node: u8,
    pub busy: bool,
    pub attempts: [u16; 2],
    pub delivered: Option<u16>,
}
/// Bounded simulated flight, including explicitly injected non-authoritative duplicate copies.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Flight {
    pub index: usize,
    pub hop: u8,
    pub due: u16,
    pub corrupt: bool,
    pub duplicate: bool,
}
/// Complete durable simulation state; trace output is retained by the orchestrator, not the checkpoint.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct State {
    pub next: u16,
    pub progress: Vec<Progress>,
    pub flights: Vec<Flight>,
}
/// Trace event uses fixed kinds only; message 0 is reserved for Python orchestration restart evidence.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Event {
    pub tick: u16,
    pub id: u16,
    pub node: u8,
    pub kind: &'static str,
}
/// Post-tick sample counts retained sender bytes, including original messages currently in flight.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Sample {
    pub tick: u16,
    pub probe_bytes: u16,
    pub relay_bytes: u16,
    pub inflight: usize,
    pub delivered: usize,
    pub expired: usize,
    pub rejected: usize,
}

/// Reflected CRC-32C for accidental corruption only; not a MAC, signature or hostile-input authenticator.
pub fn crc32c(bytes: &[u8]) -> u32 {
    let mut crc = !0_u32;
    for byte in bytes {
        crc ^= u32::from(*byte);
        for _ in 0..8 {
            crc = (crc >> 1) ^ if crc & 1 == 1 { 0x82f6_3b78 } else { 0 };
        }
    }
    !crc
}
/// Bounded ASCII hex decoding with no unchecked indexing or forgiving whitespace normalization.
pub fn unhex(text: &str, cap: usize) -> Result<Vec<u8>, &'static str> {
    if text.len() > cap * 2 || !text.len().is_multiple_of(2) {
        return Err("hex length");
    }
    text.as_bytes()
        .as_chunks::<2>()
        .0
        .iter()
        .map(|pair| {
            let high = (pair[0] as char).to_digit(16).ok_or("hex digit")?;
            let low = (pair[1] as char).to_digit(16).ok_or("hex digit")?;
            Ok(((high << 4) | low) as u8)
        })
        .collect()
}
/// Canonical lowercase hex; only numeric byte formatting enters JSON/checkpoint output.
pub fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}
/// Parse bounded unsigned decimal tokens; signed/nondecimal/overflowed input is rejected.
fn decimal(value: &str) -> Result<u16, &'static str> {
    if value.is_empty() || !value.bytes().all(|b| b.is_ascii_digit()) {
        return Err("integer");
    }
    value.parse().map_err(|_| "integer range")
}

impl Case {
    /// Parse complete lab envelope before emitting any result; never accept arbitrary addresses/files.
    pub fn parse(text: &str) -> Result<(Self, Option<String>), &'static str> {
        if text.len() > 16_384 || !text.is_ascii() {
            return Err("input size/encoding");
        }
        let mut lines = text.lines();
        let header: Vec<_> = lines.next().ok_or("header")?.split_whitespace().collect();
        if header.len() != 7 || header[0] != "DTN1" {
            return Err("header");
        }
        let numbers: Vec<u16> = header[1..]
            .iter()
            .map(|s| decimal(s))
            .collect::<Result<_, _>>()?;
        let mut case = Self {
            horizon: numbers[0],
            capacity: numbers[1],
            delay: numbers[2],
            policy: numbers[3] as u8,
            fault: numbers[4] as u8,
            pause: numbers[5],
            messages: Vec::new(),
            contacts: Vec::new(),
        };
        if !(1..=64).contains(&case.horizon)
            || ![8, 16, 32].contains(&case.capacity)
            || ![1, 3, 5].contains(&case.delay)
            || numbers[3] > 1
            || numbers[4] > 2
            || case.pause > case.horizon
        {
            return Err("settings");
        }
        let mut checkpoint = None;
        for line in lines {
            let fields: Vec<_> = line.split_whitespace().collect();
            match fields.as_slice() {
                ["M", id, release, ttl, payload] => {
                    if case.messages.len() >= 32 {
                        return Err("message count");
                    }
                    let message = Message {
                        id: decimal(id)?,
                        release: decimal(release)?,
                        ttl: decimal(ttl)?,
                        payload: unhex(payload, 16)?,
                    };
                    if !(1..=32).contains(&message.id)
                        || message.release >= case.horizon
                        || !(1..=64).contains(&message.ttl)
                        || message.payload.is_empty()
                    {
                        return Err("message range");
                    }
                    case.messages.push(message);
                }
                ["C", hop, start, end] => {
                    if case.contacts.len() >= 32 {
                        return Err("contact count");
                    }
                    let hop = decimal(hop)?;
                    let contact = Contact {
                        hop: hop as u8,
                        start: decimal(start)?,
                        end: decimal(end)?,
                    };
                    if hop > 1 || contact.start >= contact.end || contact.end > case.horizon {
                        return Err("contact range");
                    }
                    case.contacts.push(contact);
                }
                ["S", data] if checkpoint.is_none() => {
                    if data.len() > 2048 {
                        return Err("checkpoint size");
                    }
                    checkpoint = Some((*data).to_owned());
                }
                _ => return Err("record"),
            }
        }
        case.messages.sort_by_key(|m| m.id);
        if case.messages.windows(2).any(|p| p[0].id == p[1].id) {
            return Err("duplicate message");
        }
        case.contacts.sort_by_key(|c| (c.hop, c.start, c.end));
        if case
            .contacts
            .windows(2)
            .any(|p| p[0].hop == p[1].hop && p[1].start < p[0].end)
        {
            return Err("overlapping contacts");
        }
        Ok((case, checkpoint))
    }
    /// Stable lab-case fingerprint excludes pause so a fresh process can continue the same experiment.
    fn fingerprint(&self) -> u32 {
        let mut text = format!(
            "{} {} {} {} {}",
            self.horizon, self.capacity, self.delay, self.policy, self.fault
        );
        for m in &self.messages {
            write!(
                text,
                " M {} {} {} {}",
                m.id,
                m.release,
                m.ttl,
                hex(&m.payload)
            )
            .expect("String write");
        }
        for c in &self.contacts {
            write!(text, " C {} {} {}", c.hop, c.start, c.end).expect("String write");
        }
        crc32c(text.as_bytes())
    }
}

impl State {
    /// Construct unreleased progress; no trace or network I/O is used for initialization.
    pub fn new(case: &Case) -> Self {
        Self {
            next: 0,
            progress: case
                .messages
                .iter()
                .map(|_| Progress {
                    status: 0,
                    node: 0,
                    busy: false,
                    attempts: [0, 0],
                    delivered: None,
                })
                .collect(),
            flights: Vec::new(),
        }
    }
    /// Measure retained bytes; sender storage is not freed merely because transmission departed.
    pub fn used(&self, case: &Case, node: u8) -> u16 {
        self.progress
            .iter()
            .zip(&case.messages)
            .filter(|(p, _)| p.status == 1 && p.node == node)
            .map(|(_, m)| m.payload.len() as u16)
            .sum()
    }
    /// Serialize a versioned bounded checkpoint with case binding and CRC; no executable serialization.
    pub fn checkpoint(&self, case: &Case) -> Vec<u8> {
        let mut bytes = b"DNC1".to_vec();
        bytes.extend(case.fingerprint().to_le_bytes());
        bytes.extend(self.next.to_le_bytes());
        bytes.push(self.progress.len() as u8);
        for p in &self.progress {
            bytes.extend([p.status, p.node, u8::from(p.busy)]);
            bytes.extend(p.attempts[0].to_le_bytes());
            bytes.extend(p.attempts[1].to_le_bytes());
            bytes.extend(p.delivered.unwrap_or(u16::MAX).to_le_bytes());
        }
        bytes.push(self.flights.len() as u8);
        for f in &self.flights {
            bytes.extend([f.index as u8, f.hop]);
            bytes.extend(f.due.to_le_bytes());
            bytes.extend([u8::from(f.corrupt), u8::from(f.duplicate)]);
        }
        bytes.extend(crc32c(&bytes).to_le_bytes());
        bytes
    }
    /// Restore into new allocations, checking version, case, CRC, exact length and ownership invariants.
    pub fn restore(case: &Case, bytes: &[u8]) -> Result<Self, &'static str> {
        if !(16..=1024).contains(&bytes.len()) || &bytes[..4] != b"DNC1" {
            return Err("checkpoint envelope");
        }
        let split = bytes.len() - 4;
        let crc = u32::from_le_bytes(bytes[split..].try_into().map_err(|_| "CRC")?);
        if crc32c(&bytes[..split]) != crc {
            return Err("checkpoint CRC");
        }
        let mut reader = Reader {
            bytes: &bytes[4..split],
            offset: 0,
        };
        if reader.u32()? != case.fingerprint() {
            return Err("checkpoint case");
        }
        let next = reader.u16()?;
        if next > case.horizon || usize::from(reader.byte()?) != case.messages.len() {
            return Err("checkpoint position/count");
        }
        let mut state = Self {
            next,
            progress: Vec::new(),
            flights: Vec::new(),
        };
        for message in &case.messages {
            let status = reader.byte()?;
            let node = reader.byte()?;
            let busy = reader.boolean()?;
            let attempts = [reader.u16()?, reader.u16()?];
            let delivered = match reader.u16()? {
                u16::MAX => None,
                n => Some(n),
            };
            if status > 4
                || node > 2
                || attempts.iter().any(|a| *a > case.horizon)
                || busy && (status != 1 || node > 1)
                || (status == 2) != (delivered.is_some())
                || status == 2 && node != 2
                || status != 2 && node == 2
                || delivered.is_some_and(|t| t >= next || t < message.release)
                || status == 0 && (node != 0 || busy || message.release < next)
            {
                return Err("checkpoint progress");
            }
            state.progress.push(Progress {
                status,
                node,
                busy,
                attempts,
                delivered,
            });
        }
        let count = reader.byte()?;
        if count > 64 {
            return Err("checkpoint flights");
        }
        for _ in 0..count {
            let index = usize::from(reader.byte()?);
            let hop = reader.byte()?;
            let due = reader.u16()?;
            let corrupt = reader.boolean()?;
            let duplicate = reader.boolean()?;
            if index >= case.messages.len()
                || hop > 1
                || due < next
                || due > case.horizon + case.delay + 1
            {
                return Err("checkpoint flight range");
            }
            state.flights.push(Flight {
                index,
                hop,
                due,
                corrupt,
                duplicate,
            });
        }
        if reader.offset != reader.bytes.len()
            || state.used(case, 0) > case.capacity
            || state.used(case, 1) > case.capacity
        {
            return Err("checkpoint trailing/capacity");
        }
        for (index, p) in state.progress.iter().enumerate() {
            let matching = state
                .flights
                .iter()
                .filter(|f| f.index == index && f.hop == p.node && !f.duplicate)
                .count();
            if p.status == 1 && matching != usize::from(p.busy) {
                return Err("checkpoint in-flight ownership");
            }
        }
        Ok(state)
    }
    /// Execute ticks in fixed phase order: expiry, releases, arrivals, departures, sample.
    pub fn advance(&mut self, case: &Case) -> (Vec<Event>, Vec<Sample>) {
        let end = if case.pause == 0 {
            case.horizon
        } else {
            case.pause
        };
        let mut events = Vec::new();
        let mut samples = Vec::new();
        for tick in self.next..end {
            for (index, m) in case.messages.iter().enumerate() {
                if self.progress[index].status == 1 && tick >= m.release + m.ttl {
                    let p = &mut self.progress[index];
                    p.status = 3;
                    p.busy = false;
                    events.push(Event {
                        tick,
                        id: m.id,
                        node: p.node,
                        kind: "expired",
                    });
                }
            }
            for (index, m) in case.messages.iter().enumerate() {
                if self.progress[index].status == 0 && m.release == tick {
                    let admitted = self.used(case, 0) + m.payload.len() as u16 <= case.capacity;
                    self.progress[index].status = if admitted { 1 } else { 4 };
                    events.push(Event {
                        tick,
                        id: m.id,
                        node: 0,
                        kind: if admitted {
                            "queued"
                        } else {
                            "source-rejected"
                        },
                    });
                }
            }
            let due: Vec<_> = self
                .flights
                .iter()
                .filter(|f| f.due == tick)
                .cloned()
                .collect();
            self.flights.retain(|f| f.due != tick);
            for flight in due {
                let index = flight.index;
                let m = &case.messages[index];
                let p = &self.progress[index];
                if flight.duplicate || p.node > flight.hop {
                    events.push(Event {
                        tick,
                        id: m.id,
                        node: flight.hop + 1,
                        kind: "duplicate-suppressed",
                    });
                    continue;
                }
                if p.status != 1 {
                    events.push(Event {
                        tick,
                        id: m.id,
                        node: flight.hop + 1,
                        kind: "stale-arrival",
                    });
                    continue;
                }
                self.progress[index].busy = false;
                let mut received = m.payload.clone();
                if flight.corrupt {
                    received[0] ^= 1;
                }
                let kind = if crc32c(&received) != crc32c(&m.payload) {
                    "integrity-rejected"
                } else if flight.hop == 0
                    && self.used(case, 1) + m.payload.len() as u16 > case.capacity
                {
                    "receiver-full"
                } else {
                    let p = &mut self.progress[index];
                    p.node = flight.hop + 1;
                    if p.node == 2 {
                        p.status = 2;
                        p.delivered = Some(tick);
                        "delivered"
                    } else {
                        "relayed"
                    }
                };
                events.push(Event {
                    tick,
                    id: m.id,
                    node: flight.hop + 1,
                    kind,
                });
            }
            for hop in 0..2 {
                if !case
                    .contacts
                    .iter()
                    .any(|c| c.hop == hop && c.start <= tick && tick < c.end)
                {
                    continue;
                }
                let mut ready: Vec<usize> = self
                    .progress
                    .iter()
                    .enumerate()
                    .filter(|(_, p)| p.status == 1 && p.node == hop && !p.busy)
                    .map(|(i, _)| i)
                    .collect();
                ready.sort_by_key(|i| {
                    let m = &case.messages[*i];
                    (
                        if case.policy == 0 {
                            m.release
                        } else {
                            m.release + m.ttl
                        },
                        m.id,
                    )
                });
                if let Some(index) = ready.first().copied() {
                    let p = &mut self.progress[index];
                    p.busy = true;
                    p.attempts[usize::from(hop)] += 1;
                    let first = index == 0 && hop == 0 && p.attempts[0] == 1;
                    self.flights.push(Flight {
                        index,
                        hop,
                        due: tick + case.delay,
                        corrupt: case.fault == 1 && first,
                        duplicate: false,
                    });
                    if case.fault == 2 && first {
                        self.flights.push(Flight {
                            index,
                            hop,
                            due: tick + case.delay + 1,
                            corrupt: false,
                            duplicate: true,
                        });
                    }
                    events.push(Event {
                        tick,
                        id: case.messages[index].id,
                        node: hop,
                        kind: "sent",
                    });
                }
            }
            samples.push(Sample {
                tick,
                probe_bytes: self.used(case, 0),
                relay_bytes: self.used(case, 1),
                inflight: self.flights.len(),
                delivered: self.progress.iter().filter(|p| p.status == 2).count(),
                expired: self.progress.iter().filter(|p| p.status == 3).count(),
                rejected: self.progress.iter().filter(|p| p.status == 4).count(),
            });
            self.next = tick + 1;
        }
        (events, samples)
    }
    /// Emit fixed JSON keys and numeric/constant values only; arbitrary input strings are never reflected.
    pub fn json(&self, case: &Case, events: &[Event], samples: &[Sample]) -> String {
        let events = events
            .iter()
            .map(|e| {
                format!(
                    "{{\"tick\":{},\"id\":{},\"node\":{},\"kind\":\"{}\"}}",
                    e.tick, e.id, e.node, e.kind
                )
            })
            .collect::<Vec<_>>()
            .join(",");
        let samples=samples.iter().map(|s|format!("{{\"tick\":{},\"probe_bytes\":{},\"relay_bytes\":{},\"inflight\":{},\"delivered\":{},\"expired\":{},\"rejected\":{}}}",s.tick,s.probe_bytes,s.relay_bytes,s.inflight,s.delivered,s.expired,s.rejected)).collect::<Vec<_>>().join(",");
        let messages=self.progress.iter().zip(&case.messages).map(|(p,m)|format!("{{\"id\":{},\"status\":\"{}\",\"node\":{},\"attempts\":{},\"delivered_tick\":{},\"crc32c\":\"{:08x}\"}}",m.id,["unreleased","retained","delivered","expired","rejected"][usize::from(p.status)],p.node,p.attempts.iter().sum::<u16>(),p.delivered.map_or(-1,i32::from),crc32c(&m.payload))).collect::<Vec<_>>().join(",");
        format!(
            "{{\"events\":[{events}],\"samples\":[{samples}],\"messages\":[{messages}],\"checkpoint\":\"{}\"}}",
            hex(&self.checkpoint(case))
        )
    }
}
/// Checked cursor for checkpoint bytes; every fixed-width read checks its complete slice first.
struct Reader<'a> {
    bytes: &'a [u8],
    offset: usize,
}
impl Reader<'_> {
    /// Read one checked byte and advance the cursor only on success.
    fn byte(&mut self) -> Result<u8, &'static str> {
        let value = *self.bytes.get(self.offset).ok_or("checkpoint truncated")?;
        self.offset += 1;
        Ok(value)
    }
    /// Decode only canonical zero/one booleans, never a truthy arbitrary byte.
    fn boolean(&mut self) -> Result<bool, &'static str> {
        match self.byte()? {
            0 => Ok(false),
            1 => Ok(true),
            _ => Err("checkpoint boolean"),
        }
    }
    /// Read a little-endian checkpoint word using checked byte reads.
    fn u16(&mut self) -> Result<u16, &'static str> {
        Ok(u16::from_le_bytes([self.byte()?, self.byte()?]))
    }
    /// Read a little-endian fingerprint/CRC word without pointer casts.
    fn u32(&mut self) -> Result<u32, &'static str> {
        Ok(u32::from_le_bytes([
            self.byte()?,
            self.byte()?,
            self.byte()?,
            self.byte()?,
        ]))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    /// Validate numeric CRC results against independent published bytes and a common check string.
    #[test]
    fn published_crc_vectors() {
        assert_eq!(crc32c(&[0; 32]), 0x8a91_36aa);
        assert_eq!(crc32c(&[255; 32]), 0x62a8_ab43);
        assert_eq!(crc32c(&(0..32).collect::<Vec<_>>()), 0x46dd_794e);
        assert_eq!(crc32c(b"123456789"), 0xe306_9283);
    }
    #[test]
    /// Check manually derived delivery and expiry-before-arrival behavior.
    fn hand_derived_delivery_and_expiry() {
        let (case, _) = Case::parse("DTN1 8 8 1 0 0 0\nM 1 0 7 aabb\nC 0 0 2\nC 1 2 3\n").unwrap();
        let mut state = State::new(&case);
        let (events, samples) = state.advance(&case);
        assert_eq!(state.progress[0].delivered, Some(3));
        assert_eq!(samples[0].probe_bytes, 2);
        assert!(events.iter().any(|e| e.kind == "delivered" && e.tick == 3));
        let mut expired = case.clone();
        expired.messages[0].ttl = 3;
        let mut state = State::new(&expired);
        state.advance(&expired);
        assert_eq!(state.progress[0].status, 3);
    }
    #[test]
    /// Compare every split boundary and reject every single-byte checkpoint bit mutation.
    fn every_boundary_restart_matches_uninterrupted() {
        let (case, _) =
            Case::parse("DTN1 32 8 3 1 2 0\nM 1 0 30 aabb\nM 2 1 10 01\nC 0 0 20\nC 1 6 30\n")
                .unwrap();
        let mut full = State::new(&case);
        let (expected_events, expected_samples) = full.advance(&case);
        for cut in 1..case.horizon {
            let mut prefix = case.clone();
            prefix.pause = cut;
            let mut state = State::new(&case);
            let (mut events, mut samples) = state.advance(&prefix);
            let bytes = state.checkpoint(&case);
            let mut resumed = State::restore(&case, &bytes).unwrap();
            let (later, tail) = resumed.advance(&case);
            events.extend(later);
            samples.extend(tail);
            assert_eq!(resumed, full);
            assert_eq!(events, expected_events);
            assert_eq!(samples, expected_samples);
            for index in 0..bytes.len() {
                let mut corrupt = bytes.clone();
                corrupt[index] ^= 1;
                assert!(State::restore(&case, &corrupt).is_err());
            }
        }
    }
    #[test]
    /// Exercise malformed framing, shortened checkpoints and case-fingerprint mismatches.
    fn malformed_envelopes_and_checkpoints() {
        for text in [
            "",
            "DTN1 32 8 1 256 0 0",
            "DTN1 32 8 1 0 0 0\nM 1 0 2 x",
            "DTN1 32 8 1 0 0 0\nC 0 2 1",
            "DTN1 32 8 1 0 0 0\nM 1 0 2 00\nM 1 0 2 00",
        ] {
            assert!(Case::parse(text).is_err());
        }
        let (case, _) = Case::parse("DTN1 32 8 1 0 0 0").unwrap();
        let bytes = State::new(&case).checkpoint(&case);
        for cut in 0..bytes.len() {
            assert!(State::restore(&case, &bytes[..cut]).is_err());
        }
        let mut other = case.clone();
        other.delay = 3;
        assert!(State::restore(&other, &bytes).is_err());
    }
    #[test]
    /// Exercise 1025 seeded hostile checkpoint envelopes without unsafe reads or panic.
    fn seeded_hostile_checkpoint_campaign() {
        let (case, _) = Case::parse("DTN1 32 8 1 0 0 0").unwrap();
        let mut seed = 0x9171_u64;
        for size in 0..1025 {
            let mut bytes = Vec::new();
            for _ in 0..size {
                seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
                bytes.push((seed >> 32) as u8);
            }
            assert!(State::restore(&case, &bytes).is_err());
        }
    }
}
