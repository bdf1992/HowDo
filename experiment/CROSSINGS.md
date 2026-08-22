# Crossings, and the one part of them that is not recomputable

A context is a resolved description of something. A crossing is what becomes
true when two resolved contexts meet: constraints, affordances, authority,
verification, and provenance that belong to the relation rather than to either
participant alone.

The question this document settles is not what crossings *are*. It is what has
to be written down before the first trial runs, and what can wait.

## The rule

**Crossings are evidence projections.** A crossing is not persisted as an
independent entity or as a context kind. A named crossing such as
`Skill × Environment` denotes a *hypothesis* about interaction between receipt
dimensions. It is instantiated only by querying evidence receipts containing
the required operands. Properties, strength, directionality, invariance, and
higher-order structure are derived from those receipts and may be recomputed as
the research model changes.

Named crossings are hypotheses. Only receipts make one instantiated.

This is the receipt inversion applied to relations, and it has a practical
consequence: the skill graph is a materialized view over evidence, not the
authority. Instead of writing edges eagerly —

```text
SkillA --good_on--> Terminal
SkillA --bad_on--> GUI
```

— receipts accumulate and the relations are derived from them, with their
uncertainty attached. If the domain taxonomy turns out to be wrong, the graph
is rebuilt without losing a single trial of experimental history.

## Analysis vocabulary — not schema

Provisional, and deliberately kept out of storage. These are claims about
interaction that evidence can support or fail to support; they are not fields,
edge types, or object kinds.

```text
A × B      Evidence supports an interaction: the joint result cannot be
           explained adequately from the operands' independent effects.

A - B      No detectable interaction on the tested axis: main effects
           suffice within current evidence.

A / B      Effects are not separately identifiable under the current
           experiment; the operands are confounded.

(A × B) + (C × D)
           Candidate higher-order interaction among already supported
           interactions.
```

Reading them this way makes each one falsifiable rather than decorative, and
`-` becomes the most useful of the four: "this skill's lift does not vary by
environment" is a finding, not an absence of one.

Directionality is asserted, not established. No observation yet distinguishes
`A × B` from `B × A`. Convention until one does: the left operand supplies the
frame. The evidence needed to overturn that convention is recorded anyway — see
below.

## What is irreversible

Everything above can be recomputed. One thing cannot: **which resolution a
trial actually ran against.** The operands, their order, and the resolver that
assembled them exist only while the container does.

So the receipt freezes exactly this block and nothing more:

```text
resolution_version
resolution_builder_id
resolution_builder_digest
resolution_operands[]        ordered
    role
    kind
    identity
    digest
resolution_digest
```

**Ordered, not a set.** Nothing currently treats `A × B` differently from
`B × A`. Recording the order costs a few bytes and preserves the evidence
needed to discover later that orientation mattered. Recovering it afterwards is
impossible.

**`role` and `kind` are separate.** The same kind of thing can play different
roles, and the digest must distinguish `Skill(foo) + Environment(bar)` from
`Environment(foo) + Skill(bar)`, and both from any three-operand resolution.

**The resolver is recorded.** Resolution may be generated rather than declared.
Two trials can carry the same skill, the same environment, and the same task
while one resolver orders verification before planning and the other reverses
it. If resolution is part of the treatment, that difference is part of the
evidence, and operands alone will not show it.

**`resolution_version` is in the hashed payload.** Canonicalization rules are
exactly the sort of thing that changes. Without a version inside the digest, a
historical digest becomes uninterpretable: a different resolution and the same
resolution serialized under new rules would be indistinguishable.

### Digest

`resolution_digest` is the SHA-256 of a canonical JSON serialization of the
version, the resolver, and the ordered operands — object keys sorted, array
order preserved, every value a quoted string inside a typed structure. It is
not a hash of concatenated context digests: concatenation loses arity, loses
role, and lets a crafted identity impersonate the surrounding syntax.

`verify_resolution()` recomputes it from the stored block, so a later reader can
check the commitment without trusting the writer.

## What stays downstream

Whether a given resolution represents `×`, `-`, `/`, `+`, transfer,
specialization, or mere coincidence is not recorded and not decided here. It is
answered from many receipts, by whatever analysis is current at the time.

Implementation: `experiment/evidence/resolution.py`.
