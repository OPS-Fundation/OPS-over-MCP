# OPS-over-MCP
MCP + OPS: An Example of OPS-over-MCP (Standardized, Reusable Prompt Context)

# MCP + OPS: An Example of OPS-over-MCP  
**Standardized, Reusable Prompt Context**

## Summary

MCP (Model Context Protocol) provides a standardized **protocol and transport layer** for communication between models, tools, and agents.  
However, MCP intentionally does **not** define how prompt context should be structured, reused, versioned, or optimized.

OPS (Open Prompt Specification) complements MCP by defining a standardized way to **package, compose, and optimize prompt context**.

In short:

- **MCP = protocol and interoperability**
- **OPS = structured, reusable, optimized prompt context**

This document presents a concrete **OPS-over-MCP** example to illustrate how both can work together **without overlapping responsibilities**.

---

## Problem Statement

Current prompt engineering practices typically suffer from:

- Ad-hoc, non-reusable prompt strings  
- Context duplication across agents and tools  
- No formal versioning or composition model  
- Tight coupling between prompts and implementations  

**MCP solves _how_ messages are exchanged.**  
**OPS solves _what_ those messages contain.**

---

## What is OPS (Open Prompt Specification)

OPS is an open specification designed to:

- Treat prompts as **first-class artifacts**
- Standardize prompt structure and intent
- Enable reuse, versioning, and composition
- Optimize context delivery under token constraints
- Apply explicit policies (safety, redaction, allowed sources)

Reference:  
👉 https://op-foundation.org/en/


---

## Why OPS over MCP?

| Concern              | MCP | OPS |
|----------------------|-----|-----|
| Transport             | ✅  | ❌  |
| Tool interoperability | ✅  | ❌  |
| Prompt structure      | ❌  | ✅  |
| Prompt reuse          | ❌  | ✅  |
| Versioning            | ❌  | ✅  |
| Context optimization  | ❌  | ✅  |

They solve **different layers of the same problem**.

---

## Design Principles

- Clear separation of concerns  
- Declarative over imperative definitions  
- Reproducible prompt rendering  
- Minimal assumptions about model behavior  
- Protocol-agnostic prompt specification  

---

## Status

This repository is a **reference demo**, not a finalized standard.

The goal is to:

- Facilitate discussion  
- Explore interoperability patterns  
- Gather feedback from the MCP community  

---

## Open Questions

- Should prompt specifications be standardized?
- Should MCP reference external prompt specifications?
- What belongs in the protocol layer vs. the content layer?

---

## Contributing

Feedback, issues, and experiments are welcome.

If you are interested in:

- Writing an RFC  
- Building a reference implementation  
- Aligning with MCP or AAIF efforts  

Please open a discussion.

---

## License

Apache License 2.0

