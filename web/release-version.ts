/**
 * Application release label by Jason Stys; exact symbols: docs/CODE_INDEX.md.
 * Function: appendReleaseVersion; variables: canonical bundled version and footer label.
 * Vite supplies the product version from package.json; no remote metadata is fetched.
 */
declare const __APP_VERSION__: string;

/** Append the canonical build version after the authored application DOM exists. */
export function appendReleaseVersion(): void {
  const footer = document.querySelector("footer");
  if (!footer) throw new Error("Application footer is missing");
  const label = document.createElement("span");
  label.dataset.releaseVersion = "";
  label.textContent = `v${__APP_VERSION__}`;
  footer.append(label);
}
