# Vocabulary

Read this in inspect mode, when auditing a HowDo, or when a reader from outside needs the local terms mapped to established practice. Guide mode — the default — does not need it.

Terms below map to established practice so a reader from outside can audit them.

| here | industry term | one-line meaning |
|---|---|---|
| paradigm | working state / context model | the inspectable understanding a request resolves against |
| map | domain model | distinctions and relations sufficient to navigate the concern |
| path | procedure / workflow | ordered steps through the map |
| precondition | design-by-contract `require` | what must be true before a consequential step; caller's obligation |
| postcondition | design-by-contract `ensure` | predicted observable effect after a consequential step; supplier's obligation |
| invariant | design-by-contract invariant | what stays true across every admitted operation |
| context | durable learner/interaction context | reusable settled lessons about how this installation should present and interact |
| agency modifier | actor / subject binding | selects whose capabilities, authority, environment, and evidence constrain this HowDo |
| rendering contract | output contract / spec | local projection for this receiver and task, informed by context but allowed to differ |
| gate | admission check | the brink between a resolved request and an admitted operation |
| operation | command / effectful call | an admitted attempt to traverse the path |
| observation | independent evidence | what can be checked about the actual result |
| residual | observed − expected | the delta that localizes what needs correction |
| settlement | controlled write-back | accept, reject, or defer a paradigm change from the residual |
| rebase | revision after accepted settlement | preserve what survived and replace only the settled layer |
| trace | run / interaction record | what happened in one HowDo, including presentation residuals; evidence, not durable truth |
| LongHow | cross-trace synthesis | compares traces and proposes reusable context lessons for settlement |
| handle | command / trigger | small word-pair naming a move over the paradigm |
