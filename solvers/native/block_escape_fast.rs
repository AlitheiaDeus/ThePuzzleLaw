// High-speed 256-bit bitboard solver for Block Escape (BFS / A* / Greedy)
// Compile: rustc -C opt-level=3 -C target-cpu=native solvers/native/block_escape_fast.rs -o solvers/native/block_escape_fast.exe

use std::cmp::Reverse;
use std::collections::BinaryHeap;
use std::io::{self, BufRead, Write};
use std::time::Instant;

#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Default)]
struct Mask256([u64; 4]);

impl Mask256 {
    #[inline(always)]
    fn is_zero(self) -> bool {
        (self.0[0] | self.0[1] | self.0[2] | self.0[3]) == 0
    }

    #[inline(always)]
    fn or(self, other: Self) -> Self {
        Mask256([
            self.0[0] | other.0[0],
            self.0[1] | other.0[1],
            self.0[2] | other.0[2],
            self.0[3] | other.0[3],
        ])
    }

    #[inline(always)]
    fn and(self, other: Self) -> Self {
        Mask256([
            self.0[0] & other.0[0],
            self.0[1] & other.0[1],
            self.0[2] & other.0[2],
            self.0[3] & other.0[3],
        ])
    }

    #[inline(always)]
    fn xor(self, other: Self) -> Self {
        Mask256([
            self.0[0] ^ other.0[0],
            self.0[1] ^ other.0[1],
            self.0[2] ^ other.0[2],
            self.0[3] ^ other.0[3],
        ])
    }

    #[inline(always)]
    fn shl(self, shift: u32) -> Self {
        if shift == 0 {
            return self;
        }
        let words = (shift / 64) as usize;
        let bits = shift % 64;
        let mut out = [0u64; 4];
        for i in words..4 {
            out[i] = self.0[i - words] << bits;
            if bits != 0 && i > words {
                out[i] |= self.0[i - words - 1] >> (64 - bits);
            }
        }
        Mask256(out)
    }

    #[inline(always)]
    fn shr(self, shift: u32) -> Self {
        if shift == 0 {
            return self;
        }
        let words = (shift / 64) as usize;
        let bits = shift % 64;
        let mut out = [0u64; 4];
        for i in 0..(4 - words) {
            out[i] = self.0[i + words] >> bits;
            if bits != 0 && i + words + 1 < 4 {
                out[i] |= self.0[i + words + 1] << (64 - bits);
            }
        }
        Mask256(out)
    }

    #[inline(always)]
    fn shift_signed(self, delta: i32) -> Self {
        if delta >= 0 {
            self.shl(delta as u32)
        } else {
            self.shr((-delta) as u32)
        }
    }

    #[inline(always)]
    fn lowest_bit_idx(self) -> usize {
        for i in 0..4 {
            if self.0[i] != 0 {
                return i * 64 + self.0[i].trailing_zeros() as usize;
            }
        }
        0
    }

    fn from_hex(s: &str) -> Self {
        let mut out = [0u64; 4];
        let mut idx = 0;
        let mut pos = s.len();
        while pos > 0 && idx < 4 {
            let start = pos.saturating_sub(16);
            out[idx] = u64::from_str_radix(&s[start..pos], 16).unwrap_or(0);
            pos = start;
            idx += 1;
        }
        Mask256(out)
    }

    fn to_hex(self) -> String {
        format!(
            "{:016x}{:016x}{:016x}{:016x}",
            self.0[3], self.0[2], self.0[1], self.0[0]
        )
    }
}

struct Action {
    is_tap: bool,
    deltas: Vec<(usize, i32)>,
}

struct GroupSpec {
    ids: Vec<usize>,
    is_ice: bool,
    actions: Vec<Action>,
}

#[inline(always)]
fn mix64(mut x: u64) -> u64 {
    x = (x ^ (x >> 30)).wrapping_mul(0xbf58476d1ce4e5b9);
    x = (x ^ (x >> 27)).wrapping_mul(0x94d049bb133111eb);
    x ^ (x >> 31)
}

fn hash_state(anchors: &[u8], pending: u16) -> u64 {
    let mut h = mix64(pending as u64 ^ 0x9e3779b97f4a7c15);
    let mut i = 0;
    while i + 8 <= anchors.len() {
        let chunk = u64::from_le_bytes([
            anchors[i],
            anchors[i + 1],
            anchors[i + 2],
            anchors[i + 3],
            anchors[i + 4],
            anchors[i + 5],
            anchors[i + 6],
            anchors[i + 7],
        ]);
        h = mix64(h ^ chunk);
        i += 8;
    }
    if i < anchors.len() {
        let mut tail = 0u64;
        let mut shift = 0;
        while i < anchors.len() {
            tail |= (anchors[i] as u64) << shift;
            shift += 8;
            i += 1;
        }
        h = mix64(h ^ tail);
    }
    h
}

struct StateTable {
    n_blocks: usize,
    arena: Vec<u8>,
    pending: Vec<u16>, // u16::MAX = None, else group idx
    parent: Vec<u32>,
    move_code: Vec<u32>, // packed (g_idx << 16) | (ld_idx << 4) | kind
    hashes: Vec<u64>,
    buckets: Vec<u32>,
}

impl StateTable {
    fn new(n_blocks: usize) -> Self {
        Self {
            n_blocks,
            arena: Vec::with_capacity(65536 * n_blocks),
            pending: Vec::with_capacity(65536),
            parent: Vec::with_capacity(65536),
            move_code: Vec::with_capacity(65536),
            hashes: Vec::with_capacity(65536),
            buckets: vec![u32::MAX; 1 << 18],
        }
    }

    #[inline(always)]
    fn get_anchors(&self, sid: u32) -> &[u8] {
        let start = sid as usize * self.n_blocks;
        &self.arena[start..start + self.n_blocks]
    }

    fn rehash(&mut self) {
        let new_cap = self.buckets.len() * 2;
        let mask = new_cap - 1;
        let mut new_buckets = vec![u32::MAX; new_cap];
        for (sid, &h) in self.hashes.iter().enumerate() {
            let mut idx = (h as usize) & mask;
            while new_buckets[idx] != u32::MAX {
                idx = (idx + 1) & mask;
            }
            new_buckets[idx] = sid as u32;
        }
        self.buckets = new_buckets;
    }

    fn insert_or_get(
        &mut self,
        canon: &[u8],
        pend: u16,
        par: u32,
        mcode: u32,
    ) -> (u32, bool) {
        let h = hash_state(canon, pend);
        self.insert_with_hash(canon, pend, h, par, mcode)
    }

    fn insert_with_hash(
        &mut self,
        canon: &[u8],
        pend: u16,
        h: u64,
        par: u32,
        mcode: u32,
    ) -> (u32, bool) {
        if (self.pending.len() + 1) * 2 >= self.buckets.len() {
            self.rehash();
        }
        let mask = self.buckets.len() - 1;
        let mut idx = (h as usize) & mask;
        loop {
            let existing = self.buckets[idx];
            if existing == u32::MAX {
                let sid = self.pending.len() as u32;
                self.arena.extend_from_slice(canon);
                self.pending.push(pend);
                self.parent.push(par);
                self.move_code.push(mcode);
                self.hashes.push(h);
                self.buckets[idx] = sid;
                return (sid, true);
            }
            if self.hashes[existing as usize] == h
                && self.pending[existing as usize] == pend
                && self.get_anchors(existing) == canon
            {
                return (existing, false);
            }
            idx = (idx + 1) & mask;
        }
    }
}

struct ExpandBuf {
    cur_masks: Vec<Mask256>,
    sim_masks: Vec<Mask256>,
    tele_masks: Vec<Mask256>,
    cand_canon: Vec<u8>,
    out_anchors: Vec<u8>,
    out_meta: Vec<(u64, u32, u32, u16)>, // (hash, parent_sid, mcode, pend)
}

impl ExpandBuf {
    fn new(n_blocks: usize) -> Self {
        Self {
            cur_masks: vec![Mask256::default(); n_blocks],
            sim_masks: vec![Mask256::default(); n_blocks],
            tele_masks: vec![Mask256::default(); n_blocks],
            cand_canon: vec![0u8; n_blocks],
            out_anchors: Vec::with_capacity(n_blocks * 64),
            out_meta: Vec::with_capacity(64),
        }
    }
}

#[inline(always)]
fn canonicalize_masks_to_anchors(raw: &[Mask256], out: &mut [u8], canon_classes: &[Vec<usize>]) {
    let mut p = 0;
    for cls in canon_classes {
        if cls.len() == 1 {
            out[p] = raw[cls[0]].lowest_bit_idx() as u8;
            p += 1;
        } else {
            let start = p;
            for &bid in cls {
                out[p] = raw[bid].lowest_bit_idx() as u8;
                p += 1;
            }
            out[start..p].sort_unstable();
        }
    }
}

#[inline(always)]
fn uncanonicalize_anchors_to_masks(
    ck: &[u8],
    raw: &mut [Mask256],
    base_shapes: &[Mask256],
    canon_classes: &[Vec<usize>],
) {
    let mut p = 0;
    for cls in canon_classes {
        for &bid in cls {
            raw[bid] = base_shapes[bid].shl(ck[p] as u32);
            p += 1;
        }
    }
}

#[inline(always)]
fn push_cand(
    masks_slice: &[Mask256],
    pend_val: u16,
    cur_sid: u32,
    mcode: u32,
    cand_canon: &mut [u8],
    canon_classes: &[Vec<usize>],
    out_anchors: &mut Vec<u8>,
    out_meta: &mut Vec<(u64, u32, u32, u16)>,
) {
    canonicalize_masks_to_anchors(masks_slice, cand_canon, canon_classes);
    let h = hash_state(cand_canon, pend_val);
    out_anchors.extend_from_slice(cand_canon);
    out_meta.push((h, cur_sid, mcode, pend_val));
}

fn expand_state_into(
    ck: &[u8],
    cur_sid: u32,
    cur_pend: u16,
    wall_mask: Mask256,
    board_mask: Mask256,
    base_shapes: &[Mask256],
    portals: &[(Mask256, Mask256)],
    groups: &[GroupSpec],
    canon_classes: &[Vec<usize>],
    glitches_allowed: bool,
    multi_step: bool,
    buf: &mut ExpandBuf,
) {
    uncanonicalize_anchors_to_masks(ck, &mut buf.cur_masks, base_shapes, canon_classes);
    let mut total_occ = Mask256::default();
    for &m in &buf.cur_masks {
        total_occ = total_occ.or(m);
    }
    let empty_mask = board_mask.xor(total_occ);

    for (g_idx, group) in groups.iter().enumerate() {
        if cur_pend != u16::MAX && g_idx != cur_pend as usize {
            continue;
        }
        let mut group_occ = Mask256::default();
        for &bid in &group.ids {
            group_occ = group_occ.or(buf.cur_masks[bid]);
        }
        let other_occ = total_occ.xor(group_occ);
        let blocked_mask = wall_mask.or(other_occ);

        for (ld_idx, act) in group.actions.iter().enumerate() {
            if act.is_tap {
                buf.sim_masks.copy_from_slice(&buf.cur_masks);
                let mut teleported = false;
                for &bid in &group.ids {
                    let bm = buf.sim_masks[bid];
                    for &(p1, p2) in portals {
                        let dest = if bm == p1 {
                            p2
                        } else if bm == p2 {
                            p1
                        } else {
                            Mask256::default()
                        };
                        if !dest.is_zero() {
                            let mut cur_other = other_occ;
                            for &ob in &group.ids {
                                if ob != bid {
                                    cur_other = cur_other.or(buf.sim_masks[ob]);
                                }
                            }
                            if dest.and(wall_mask.or(cur_other)).is_zero() {
                                buf.sim_masks[bid] = dest;
                                teleported = true;
                            }
                            break;
                        }
                    }
                }
                if teleported {
                    let mcode = ((g_idx as u32) << 16) | ((ld_idx as u32) << 4) | 0;
                    push_cand(
                        &buf.sim_masks,
                        u16::MAX,
                        cur_sid,
                        mcode,
                        &mut buf.cand_canon,
                        canon_classes,
                        &mut buf.out_anchors,
                        &mut buf.out_meta,
                    );
                }
                continue;
            }

            if group.ids.len() == 1 {
                let (b0, d0) = act.deltas[0];
                if buf.cur_masks[b0].shift_signed(d0).and(empty_mask.or(buf.cur_masks[b0])).is_zero() {
                    continue;
                }
            }

            buf.sim_masks.copy_from_slice(&buf.cur_masks);
            let mut stepped = false;
            loop {
                let mut collision = false;
                for &(bid, delta) in &act.deltas {
                    let nm = buf.sim_masks[bid].shift_signed(delta);
                    if !nm.and(blocked_mask).is_zero() {
                        collision = true;
                        break;
                    }
                }
                if collision {
                    break;
                }
                for &(bid, delta) in &act.deltas {
                    buf.sim_masks[bid] = buf.sim_masks[bid].shift_signed(delta);
                }
                stepped = true;
                if !group.is_ice {
                    if !portals.is_empty() {
                        buf.tele_masks.copy_from_slice(&buf.sim_masks);
                        let mut teleported = false;
                        for &bid in &group.ids {
                            let bm = buf.tele_masks[bid];
                            for &(p1, p2) in portals {
                                let dest = if bm == p1 {
                                    p2
                                } else if bm == p2 {
                                    p1
                                } else {
                                    Mask256::default()
                                };
                                if !dest.is_zero() {
                                    let mut cur_other = other_occ;
                                    for &ob in &group.ids {
                                        if ob != bid {
                                            cur_other = cur_other.or(buf.tele_masks[ob]);
                                        }
                                    }
                                    if dest.and(wall_mask.or(cur_other)).is_zero() {
                                        buf.tele_masks[bid] = dest;
                                        teleported = true;
                                    }
                                    break;
                                }
                            }
                        }
                        if teleported {
                            let mcode2 = ((g_idx as u32) << 16) | ((ld_idx as u32) << 4) | 2;
                            push_cand(
                                &buf.tele_masks,
                                u16::MAX,
                                cur_sid,
                                mcode2,
                                &mut buf.cand_canon,
                                canon_classes,
                                &mut buf.out_anchors,
                                &mut buf.out_meta,
                            );
                            if glitches_allowed {
                                let mcode3 = ((g_idx as u32) << 16) | ((ld_idx as u32) << 4) | 3;
                                push_cand(
                                    &buf.sim_masks,
                                    g_idx as u16,
                                    cur_sid,
                                    mcode3,
                                    &mut buf.cand_canon,
                                    canon_classes,
                                    &mut buf.out_anchors,
                                    &mut buf.out_meta,
                                );
                            }
                        } else {
                            let mcode1 = ((g_idx as u32) << 16) | ((ld_idx as u32) << 4) | 1;
                            push_cand(
                                &buf.sim_masks,
                                u16::MAX,
                                cur_sid,
                                mcode1,
                                &mut buf.cand_canon,
                                canon_classes,
                                &mut buf.out_anchors,
                                &mut buf.out_meta,
                            );
                        }
                    } else {
                        let mcode1 = ((g_idx as u32) << 16) | ((ld_idx as u32) << 4) | 1;
                        push_cand(
                            &buf.sim_masks,
                            u16::MAX,
                            cur_sid,
                            mcode1,
                            &mut buf.cand_canon,
                            canon_classes,
                            &mut buf.out_anchors,
                            &mut buf.out_meta,
                        );
                    }
                    if !multi_step {
                        break;
                    }
                }
            }
            if !stepped || !group.is_ice {
                continue;
            }

            if !portals.is_empty() {
                buf.tele_masks.copy_from_slice(&buf.sim_masks);
                let mut teleported = false;
                for &bid in &group.ids {
                    let bm = buf.tele_masks[bid];
                    for &(p1, p2) in portals {
                        let dest = if bm == p1 {
                            p2
                        } else if bm == p2 {
                            p1
                        } else {
                            Mask256::default()
                        };
                        if !dest.is_zero() {
                            let mut cur_other = other_occ;
                            for &ob in &group.ids {
                                if ob != bid {
                                    cur_other = cur_other.or(buf.tele_masks[ob]);
                                }
                            }
                            if dest.and(wall_mask.or(cur_other)).is_zero() {
                                buf.tele_masks[bid] = dest;
                                teleported = true;
                            }
                            break;
                        }
                    }
                }
                if teleported {
                    let mcode2 = ((g_idx as u32) << 16) | ((ld_idx as u32) << 4) | 2;
                    push_cand(
                        &buf.tele_masks,
                        u16::MAX,
                        cur_sid,
                        mcode2,
                        &mut buf.cand_canon,
                        canon_classes,
                        &mut buf.out_anchors,
                        &mut buf.out_meta,
                    );
                    if glitches_allowed {
                        let mcode3 = ((g_idx as u32) << 16) | ((ld_idx as u32) << 4) | 3;
                        push_cand(
                            &buf.sim_masks,
                            g_idx as u16,
                            cur_sid,
                            mcode3,
                            &mut buf.cand_canon,
                            canon_classes,
                            &mut buf.out_anchors,
                            &mut buf.out_meta,
                        );
                    }
                    continue;
                }
            }
            let mcode1 = ((g_idx as u32) << 16) | ((ld_idx as u32) << 4) | 1;
            push_cand(
                &buf.sim_masks,
                u16::MAX,
                cur_sid,
                mcode1,
                &mut buf.cand_canon,
                canon_classes,
                &mut buf.out_anchors,
                &mut buf.out_meta,
            );
        }
    }
}

fn main() {
    let stdin = io::stdin();
    let mut lines = stdin.lock().lines();
    let next_line = |ls: &mut io::Lines<io::StdinLock>| -> Vec<String> {
        ls.next()
            .expect("eof")
            .expect("io")
            .split_whitespace()
            .map(|s| s.to_string())
            .collect()
    };

    let hdr = next_line(&mut lines);
    let n_blocks: usize = hdr[0].parse().unwrap();
    let t_id: usize = hdr[1].parse().unwrap();
    let search_mode = hdr[2].clone();
    let glitches_allowed = hdr[3] == "1";
    let multi_step = hdr.get(4).map(|s| s == "1").unwrap_or(true);

    let masks_line = next_line(&mut lines);
    let wall_mask = Mask256::from_hex(&masks_line[0]);
    let board_mask = Mask256::from_hex(&masks_line[1]);
    let target_mask = Mask256::from_hex(&masks_line[2]);

    let init_line = next_line(&mut lines);
    let init_masks: Vec<Mask256> = init_line.iter().map(|s| Mask256::from_hex(s)).collect();

    let n_portals: usize = next_line(&mut lines)[0].parse().unwrap();
    let mut portals = Vec::with_capacity(n_portals);
    for _ in 0..n_portals {
        let p = next_line(&mut lines);
        portals.push((Mask256::from_hex(&p[0]), Mask256::from_hex(&p[1])));
    }

    let n_groups: usize = next_line(&mut lines)[0].parse().unwrap();
    let mut groups = Vec::with_capacity(n_groups);
    for _ in 0..n_groups {
        let g = next_line(&mut lines);
        let is_ice = g[0] == "1";
        let n_ids: usize = g[1].parse().unwrap();
        let ids: Vec<usize> = g[2..2 + n_ids].iter().map(|s| s.parse().unwrap()).collect();
        let n_acts: usize = next_line(&mut lines)[0].parse().unwrap();
        let mut actions = Vec::with_capacity(n_acts);
        for _ in 0..n_acts {
            let a = next_line(&mut lines);
            if a[0] == "T" {
                actions.push(Action {
                    is_tap: true,
                    deltas: Vec::new(),
                });
            } else {
                let k: usize = a[1].parse().unwrap();
                let mut deltas = Vec::with_capacity(k);
                for j in 0..k {
                    let bid: usize = a[2 + 2 * j].parse().unwrap();
                    let d: i32 = a[3 + 2 * j].parse().unwrap();
                    deltas.push((bid, d));
                }
                actions.push(Action {
                    is_tap: false,
                    deltas,
                });
            }
        }
        groups.push(GroupSpec {
            ids,
            is_ice,
            actions,
        });
    }

    let n_classes: usize = next_line(&mut lines)[0].parse().unwrap();
    let mut canon_classes = Vec::with_capacity(n_classes);
    let mut t_canon_idx = 0usize;
    let mut pos = 0usize;
    for _ in 0..n_classes {
        let c = next_line(&mut lines);
        let k: usize = c[0].parse().unwrap();
        let cls: Vec<usize> = c[1..1 + k].iter().map(|s| s.parse().unwrap()).collect();
        if k == 1 && cls[0] == t_id {
            t_canon_idx = pos;
        }
        pos += k;
        canon_classes.push(cls);
    }

    let mut dist_map = [0u32; 256];
    let dline = next_line(&mut lines);
    let n_dist: usize = dline[0].parse().unwrap();
    for i in 0..n_dist {
        let idx: usize = dline[1 + 2 * i].parse().unwrap();
        let val: u32 = dline[2 + 2 * i].parse().unwrap();
        if idx < 256 {
            dist_map[idx] = val;
        }
    }

    let base_shapes: Vec<Mask256> = init_masks
        .iter()
        .map(|&m| m.shr(m.lowest_bit_idx() as u32))
        .collect();
    let target_anchor_u8: u8 = target_mask.lowest_bit_idx() as u8;

    let mut table = StateTable::new(n_blocks);
    let mut init_canon = vec![0u8; n_blocks];
    canonicalize_masks_to_anchors(&init_masks, &mut init_canon, &canon_classes);
    let (init_sid, _) = table.insert_or_get(&init_canon, u16::MAX, u32::MAX, 0);

    let mut solved_sid: Option<u32> = None;
    let mut last_report = Instant::now();
    let stdout = io::stdout();
    let mut out = stdout.lock();

    if search_mode == "astar" || search_mode == "wastar" || search_mode == "greedy" {
        let is_greedy = search_mode == "greedy";
        let h_weight: u32 = if search_mode == "wastar" { 3 } else { 1 };
        let mut g_scores = vec![u32::MAX; 1];
        g_scores[0] = 0;
        let h0 = dist_map[init_canon[t_canon_idx] as usize] * h_weight;
        let mut heap: BinaryHeap<Reverse<(u32, u32, u32)>> = BinaryHeap::new();
        heap.push(Reverse((h0, 0, init_sid)));
        let mut buf = ExpandBuf::new(n_blocks);

        while let Some(Reverse((_, cur_g, cur_sid))) = heap.pop() {
            if cur_g > g_scores[cur_sid as usize] {
                continue;
            }
            let cur_pend = table.pending[cur_sid as usize];
            {
                let ck = table.get_anchors(cur_sid);
                if cur_pend == u16::MAX && ck[t_canon_idx] == target_anchor_u8 {
                    solved_sid = Some(cur_sid);
                    break;
                }
            }

            if last_report.elapsed().as_millis() >= 500 {
                last_report = Instant::now();
                let _ = writeln!(out, "PROG {} {}", table.pending.len(), cur_g);
                let _ = out.flush();
            }

            buf.out_anchors.clear();
            buf.out_meta.clear();
            {
                let ck = table.get_anchors(cur_sid);
                expand_state_into(
                    ck,
                    cur_sid,
                    cur_pend,
                    wall_mask,
                    board_mask,
                    &base_shapes,
                    &portals,
                    &groups,
                    &canon_classes,
                    glitches_allowed,
                    multi_step,
                    &mut buf,
                );
            }

            let nxt_g = cur_g + 1;
            for (idx, &(h, _, mcode, pend_val)) in buf.out_meta.iter().enumerate() {
                let cand = &buf.out_anchors[idx * n_blocks..(idx + 1) * n_blocks];
                let (nsid, is_new) = table.insert_with_hash(cand, pend_val, h, cur_sid, mcode);
                if is_new {
                    g_scores.push(nxt_g);
                } else if nxt_g < g_scores[nsid as usize] {
                    g_scores[nsid as usize] = nxt_g;
                    table.parent[nsid as usize] = cur_sid;
                    table.move_code[nsid as usize] = mcode;
                } else {
                    continue;
                }
                let heur = dist_map[cand[t_canon_idx] as usize];
                let f = if is_greedy { heur } else { nxt_g + heur * h_weight };
                heap.push(Reverse((f, nxt_g, nsid)));
            }
        }
    } else {
        // Multi-core level-synchronous parallel BFS
        let n_threads = std::thread::available_parallelism()
            .map(|n| n.get())
            .unwrap_or(1)
            .min(16);
        let mut level_start: usize = 0;
        let mut level_end: usize = 1;
        let mut cur_depth: u32 = 0;
        let mut seq_buf = ExpandBuf::new(n_blocks);

        while level_start < level_end {
            for sid in level_start..level_end {
                if table.pending[sid] == u16::MAX && table.get_anchors(sid as u32)[t_canon_idx] == target_anchor_u8 {
                    solved_sid = Some(sid as u32);
                    break;
                }
            }
            if solved_sid.is_some() {
                break;
            }

            let mut batch_start = level_start;
            while batch_start < level_end {
                let batch_end = (batch_start + 16384).min(level_end);
                if last_report.elapsed().as_millis() >= 500 {
                    last_report = Instant::now();
                    let _ = writeln!(out, "PROG {} {}", table.pending.len(), cur_depth);
                    let _ = out.flush();
                }

                let batch_len = batch_end - batch_start;
                if n_threads <= 1 || batch_len < 64 {
                    seq_buf.out_anchors.clear();
                    seq_buf.out_meta.clear();
                    for sid in batch_start..batch_end {
                        let ck = table.get_anchors(sid as u32);
                        let pend = table.pending[sid];
                        expand_state_into(
                            ck,
                            sid as u32,
                            pend,
                            wall_mask,
                            board_mask,
                            &base_shapes,
                            &portals,
                            &groups,
                            &canon_classes,
                            glitches_allowed,
                            multi_step,
                            &mut seq_buf,
                        );
                    }
                    for (idx, &(h, par_sid, mcode, pend_val)) in seq_buf.out_meta.iter().enumerate() {
                        let cand = &seq_buf.out_anchors[idx * n_blocks..(idx + 1) * n_blocks];
                        table.insert_with_hash(cand, pend_val, h, par_sid, mcode);
                    }
                } else {
                    let workers = n_threads.min(batch_len / 16).max(1);
                    let chunk = (batch_len + workers - 1) / workers;
                    let table_ref = &table;
                    let shapes_ref = &base_shapes;
                    let portals_ref = &portals;
                    let groups_ref = &groups;
                    let classes_ref = &canon_classes;

                    let worker_outputs: Vec<ExpandBuf> = std::thread::scope(|s| {
                        let mut handles = Vec::with_capacity(workers);
                        for w in 0..workers {
                            let ws = batch_start + w * chunk;
                            let we = (ws + chunk).min(batch_end);
                            if ws >= we {
                                continue;
                            }
                            handles.push(s.spawn(move || {
                                let mut wbuf = ExpandBuf::new(n_blocks);
                                for sid in ws..we {
                                    let ck = table_ref.get_anchors(sid as u32);
                                    let pend = table_ref.pending[sid];
                                    expand_state_into(
                                        ck,
                                        sid as u32,
                                        pend,
                                        wall_mask,
                                        board_mask,
                                        shapes_ref,
                                        portals_ref,
                                        groups_ref,
                                        classes_ref,
                                        glitches_allowed,
                                        multi_step,
                                        &mut wbuf,
                                    );
                                }
                                wbuf
                            }));
                        }
                        handles.into_iter().map(|h| h.join().unwrap()).collect()
                    });

                    for wbuf in &worker_outputs {
                        for (idx, &(h, par_sid, mcode, pend_val)) in wbuf.out_meta.iter().enumerate() {
                            let cand = &wbuf.out_anchors[idx * n_blocks..(idx + 1) * n_blocks];
                            table.insert_with_hash(cand, pend_val, h, par_sid, mcode);
                        }
                    }
                }
                batch_start = batch_end;
            }

            level_start = level_end;
            level_end = table.pending.len();
            cur_depth += 1;
        }
    }

    if let Some(end_sid) = solved_sid {
        let mut steps: Vec<(u32, u32)> = Vec::new();
        let mut cur = end_sid;
        while table.parent[cur as usize] != u32::MAX {
            steps.push((cur, table.move_code[cur as usize]));
            cur = table.parent[cur as usize];
        }
        steps.reverse();
        let _ = writeln!(out, "SOL {} {}", steps.len(), table.pending.len());
        let mut raw = vec![Mask256::default(); n_blocks];
        for (sid, mcode) in steps {
            uncanonicalize_anchors_to_masks(table.get_anchors(sid), &mut raw, &base_shapes, &canon_classes);
            let hexes: Vec<String> = raw.iter().map(|m| m.to_hex()).collect();
            let _ = writeln!(out, "{} {}", mcode, hexes.join(" "));
        }
    } else {
        let _ = writeln!(out, "FAIL {}", table.pending.len());
    }
    let _ = out.flush();
}
