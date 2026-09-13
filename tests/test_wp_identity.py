from blog_engine.wp_identity import TARGET, plan_changes


def test_plans_only_fields_that_differ():
    settings = {"title": "Robert Dugger — Dev Blog", "description": TARGET["description"]}
    user = {"name": "Robert Dugger", "url": ""}
    changes = plan_changes(settings, user)
    assert {(c["endpoint"], c["field"]) for c in changes} == {("settings", "title"), ("users/me", "name"), ("users/me", "url")}


def test_no_changes_when_already_correct():
    settings = {"title": TARGET["title"], "description": TARGET["description"]}
    user = {"name": TARGET["name"], "url": TARGET["url"]}
    assert plan_changes(settings, user) == []
