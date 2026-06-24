"""FastAPI surface for Atlas. The deterministic endpoints never call a model; only
/extract (and the extract half of /assess/control) do, and only via extraction/."""
