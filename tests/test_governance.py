from meg.governance.policy import allowed


def test_readonly_is_denied_restricted_and_developer_can_write_internal() -> None:
    policies = [{"agent_role": "readonly", "action": "read", "effect": "allow", "max_sensitivity": "public"},
                {"agent_role": "developer", "action": "write", "effect": "allow", "max_sensitivity": "internal"}]
    assert allowed("readonly", "read", "restricted", policies)[0] is False
    assert allowed("developer", "write", "internal", policies)[0] is True
