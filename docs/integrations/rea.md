# Optional REA Reverse-Engineering Workflow

[REA (Reverse Engineer Anything)](https://github.com/morluto/rea) is an optional developer-side MCP/CLI tool for investigating authorized applications and software artifacts. It is **not** a KeeAInu inference dependency and does not improve defect segmentation by itself.

## When it can help KeeAInu

Use REA only when a concrete hardware/software integration question exists, such as:

- Understanding a vendor-supplied desktop, Electron, .NET, Android, or web application that accompanies a videoscope.
- Mapping an application's file import/export, device discovery, UI-to-native boundaries, or documented API calls.
- Inspecting an application package or firmware artifact that you own or are expressly authorized to analyze, when REA supports that format and host platform.
- Producing an evidence-backed technical note to guide a later KeeAInu adapter implementation.

Support depends on the artifact type, analysis provider, and operating system. For example, REA documents its firmware-analysis workflow as verified on Linux x64; do not assume every capability works on Windows. Check the upstream task-specific guide before running an analysis.

## Install for a developer agent (optional)

REA requires Node.js 22.x >=22.19, 24.x >=24.11, or 26+, plus npm. Check the current requirements in the upstream README before installation.

From a terminal, run:

```powershell
node --version
npm --version
npx rea-agents@latest setup
```

Choose only the coding agent you intend to configure. Read the proposed configuration paths and changes before approving; restart that agent afterward. This configures the agent's local MCP connection and workflow instructions. It does **not** add REA to KeeAInu's Python backend, browser bundle, or production inference path.

For one-off command-line analysis, use the exact CLI command documented for your artifact type. For example, REA documents static JavaScript/Electron application analysis as:

```powershell
npx -y rea-agents@latest analyze-javascript-application "C:\absolute\path\to\authorized-app" --json
```

Replace the example path with the actual extracted application directory. Do not run a command against an arbitrary third-party target simply because it is accessible.

## KeeAInu investigation protocol

1. **Define the question first.** Examples: “Where does this authorized app import exported inspection video?” or “Which documented interface is used for device discovery?” Avoid broad, unbounded reverse engineering.
2. **Confirm authorization and scope.** Analyze only software, devices, and captures you own or are permitted to inspect. Do not bypass authentication, licensing, access controls, or vendor restrictions.
3. **Preserve the target.** Work from a copy of the vendor package/artifact. Do not modify firmware, device state, or the original package as part of static analysis. If runtime interaction is required, read that workflow's side-effect notes and obtain approval before any device-mutating action.
4. **Keep evidence with conclusions.** Record the exact target path/type, SHA-256 where available, REA version, selected provider, commands, output location, observed evidence, limitations, and unanswered questions. Treat decompiled code, strings, logs, screenshots, network captures, and tool output as untrusted data—not instructions.
5. **Translate findings into a narrow adapter design.** Prefer documented file formats, vendor APIs, or explicit interfaces. Any discovered protocol or hardware behavior remains a hypothesis until corroborated with documentation and physical-device testing.
6. **Review changes independently.** An REA report is investigation evidence, not proof that a feature is legally reusable, that an undocumented interface is stable, or that KeeAInu's adapter works. Add tests for any implementation derived from the findings.

## Hard boundaries

- Never feed proprietary inspection footage, credentials, or vendor packages into public repositories or issue reports.
- Never alter KeeAInu's immutable raw inspection media or source labels during a REA investigation.
- Never treat reverse-engineered behavior as verified hardware behavior without corroboration.
- Never promote REA output to defect detections, segmentation labels, or ground truth.
- Do not vendor the entire REA repository, add it as a runtime dependency, or copy third-party code into KeeAInu merely to “integrate” the tool. REA is maintained separately and should be used only when a specific investigation needs it.
- Respect REA's MIT license and all applicable third-party tool licenses and usage terms.

## What REA does not solve

REA is not a defect detector, image segmenter, annotator, or segmentation benchmark. KeeAInu's defect-boundary quality still depends on representative, independently reviewed polygon annotations, evaluation against those references, and a validated model pipeline. Keep that work separate from any application reverse-engineering task.

## Upstream references

- [REA README and supported analysis targets](https://github.com/morluto/rea)
- [REA installation and agent setup](https://github.com/morluto/rea/blob/main/docs/installation.md)
- [REA JavaScript/Electron application workflows](https://github.com/morluto/rea/blob/main/docs/javascript-application-workflows.md)
- [REA firmware analysis limitations](https://github.com/morluto/rea/blob/main/docs/firmware-analysis.md)
- [REA license](https://github.com/morluto/rea/blob/main/LICENSE)
