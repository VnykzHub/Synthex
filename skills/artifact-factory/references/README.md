# Artifact Factory — Reference

## YAML Template with Variable Substitution

```yaml
# template: component.yaml.j2
name: "{{ component.name }}"
version: "{{ component.version | default('0.1.0') }}"
dependencies:
{% for dep in component.deps %}
  - "{{ dep }}"
{% endfor %}
spec:
  replicas: {{ spec.replicas | default(1) }}
  image: "{{ registry }}/{{ component.name }}:{{ tag }}"
```

## Markdown Template

```markdown
# {{ page.title }}

> {{ page.description }}

## Usage

\```{{ page.lang }}
{{ page.example_code }}
\```

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
{% for p in params %}
| `{{ p.name }}` | `{{ p.type }}` | `{{ p.default }}` | {{ p.desc }} |
{% endfor %}
```

## Code Template with Substitution

```python
# template: service.py.j2
from {{ lib }} import {{ imports | join(', ') }}

class {{ class_name }}{{ base_class }}:
    def __init__(self, config: dict):
        self.config = config
{% for prop in properties %}
        self.{{ prop.name }} = config.get("{{ prop.key }}", {{ prop.default }})
{% endfor %}

    def run(self) -> {{ return_type }}:
        {{ method_body | indent(8) }}
```

## Test Template

```python
# template: test_service.py.j2
import pytest
from {{ module }} import {{ class_name }}

class Test{{ class_name }}:
    @pytest.fixture
    def instance(self):
        return {{ class_name }}({{ fixture_kwargs }})

{% for case in test_cases %}
    def test_{{ case.name }}(self, instance):
        result = instance.{{ case.method }}({{ case.inputs }})
        assert result {{ case.assertion }}
{% endfor %}
```

## Variable Substitution Rules

- Use `{{ double_curly }}` for Jinja2-compatible syntax.
- Provide a `variables.json` sidecar file alongside templates for non-interactive rendering.
- Reference sensitive values as `{{ env.VAR_NAME }}` and maintain a `.env.example`.
- Validate all substitutions with a dry-run flag before writing output files.
