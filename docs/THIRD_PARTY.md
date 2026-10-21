# Third-party context and notices

Author: Jason Stys. Project source: MIT, [LICENSE](../LICENSE). No downloaded dataset, credentials or third-party artwork is included. Every message/contact case is invented; screenshots show this application. Visuals are source-native CSS/SVG, not generated bitmap artwork.

## Runtime distributions

- CPython is distributed under the PSF license and bundled notices in `licenses/PYTHON.txt`; portable builds include them.
- Rust's standard library is MIT/Apache-2.0 with additional applicable component notices. The pinned toolchain's **actual** `share/doc/rust/COPYRIGHT-library.html` and linked `licenses/` directory are copied into each bundle, together with `licenses/RUST-MIT.txt` and `RUST-APACHE.txt`. No external Cargo crates are used.
- PyInstaller's bootloader/packaging exception permits distributing bundled applications under their own licenses. Builds copy the installed locked distribution's `COPYING.txt` into the bundle. Review that complete notice for terms; this summary is not a substitute.
- The website build uses TypeScript, Vite and their locked development dependencies. Tests use Vitest, Playwright and axe-core. Development packages are not asserted to share this project's MIT license; their package notices remain with their distributions. Browsers and development toolchains are not included as app installers.

Each ZIP includes the whole `MissionNetworkLab` directory and runtime resource/license files; keep it intact. No claim is made that builds are reproducible byte-for-byte across machines, code-signed, notarized or mission certified.

## Primary references used for concepts and validation

- [IETF RFC 9171, Bundle Protocol Version 7](https://www.rfc-editor.org/rfc/rfc9171.html): store/carry/forward and lifetime context. This lab is **not** an implementation of BPv7, CBOR blocks or convergence layers.
- [IETF RFC 9172, Bundle Protocol Security](https://www.rfc-editor.org/rfc/rfc9172.html): distinguishes security services from corruption checks. BPSec is not implemented.
- [IETF RFC 3720 Appendix B.4](https://www.rfc-editor.org/rfc/rfc3720.html#appendix-B.4): published CRC-32C input/output test vectors. Original bit-loop and table-based implementations test numeric reflected values; transmitted byte order is documented separately.

References informed original design and numeric tests. No RFC prose or code implementation is reproduced. No agency, standards-body or employer endorsement is implied.
