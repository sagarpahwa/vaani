"""POC database layer (mock DB only).

All modules here target the isolated POC Mongo (`*_mock` database on :27018).
They must never connect to the real `public_speaking_intelligence` DB — the
`assert_mock_target` guard in `init_mock_db` enforces this at runtime.
"""
