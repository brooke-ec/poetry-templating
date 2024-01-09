# Templating Poetry Plugin

[![Poetry](https://img.shields.io/endpoint?url=https://python-poetry.org/badge/v0.json)](https://python-poetry.org/)
[![PyPI - Version](https://img.shields.io/pypi/v/poetry-templating)
](https://pypi.org/project/poetry-templating/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/poetry-templating)](https://pypi.org/project/poetry-templating/)
[![Coverage Status](https://img.shields.io/coverallsCoverage/github/NimajnebEC/poetry-templating)](https://coveralls.io/github/NimajnebEC/poetry-templating?branch=main)
[![GitHub Workflow Status (with event)](https://img.shields.io/github/actions/workflow/status/nimajnebec/poetry-templating/test.yml)
](https://github.com/NimajnebEC/poetry-templating/actions)

A plugin for [Poetry](https://python-poetry.org/) which lets you substitute text on build. This plugin was created to allow you to keep a single source of truth for package wide properties such as version and author.

## Installation

The easiest way to install the plugin is via the [`self add`](https://python-poetry.org/docs/cli/#self-add) command of Poetry.

```
poetry self add poetry-templating
```

If you used `pipx` to install Poetry you can add the plugin via the `pipx inject` command.

```
pipx inject poetry poetry-templating
```

Otherwise, if you used `pip` to install Poetry you can add the plugin packages via the `pip install` command.

```
pip install poetry-templating
```

## Usage

Poetry Templating uses 'template slots' as placeholders and definitions for what they should be replaced with. Consider the following file:

```py
__version__ = "${pyproject.tool.poetry.version}"
```

When evaluated, the slot will be replaced with the `tool.poetry.version` property from `pyproject.toml`, for example:

```py
__version__ = "1.2.3"
```

Slots can also be used in conjunction with comments to add entire lines only present in the built package. This can be used with `# templating: delete` to significantly change functionality in the built package, for example:

```py
production = false # templating: delete
# ${"production = true"}

becomes

production = true
```

## Evaluating Templates

Poetry Templating will automatically evaluate template slots when building the package distributables with the `poetry build` command. You can also evaluate the project in-place by running the `poetry templating evaluate` command.

## Constructs

Poetry Templating features a number of constructs which can be used in template slots.

### Literal Construct

Denoted by quotes or double quotes, literal constructs simply replace the slot with the text within.

```
${"Hello World"}

becomes

Hello World
```

Template slots within literal constructs are also evaluated, allowing for basic string concatenation, for example:

```py
# ${"__version__ = ${pyproject.tool.poetry.version}"}

becomes

__version__ = "1.2.3"

```

### PyProject Construct

Allows you to refernce values from the package's `pyproject.toml` file.

```
${pyproject.tool.poetry.version}
${pyproject.tool.poetry.authors.0}

becomes

1.2.3
John Doe <john.doe@example.com
```

### Environment Variable Construct

Allows you to reference the buildtime environment variables.

```
${env.HOME}

becomes

/home/example/
```

### File Construct

Denoted with a forward slash, or `./` for relative files, the file construct gets the entire content of an arbitrary file.

```
${/LICENCE}

becomes

MIT License

Permission is hereby granted ...
```

## Configuration

Poetry Templating can be configured in your `pyproject.toml` file under the `tool.poetry_templating` table.

| key      | default   | description                                                                    |
| -------- | --------- | ------------------------------------------------------------------------------ |
| encoding | "utf-8"   | The text encoding to use when processing files.                                |
| include  | ["\*.py"] | A list of glob patterns for files to process.                                  |
| exclude  | []        | A list of glob patterns for files not to process, has priority over `include`. |

Poetry Templating can also be enabled and disabled within a single file:

```py
# templating: off
example = "${'will NOT get evaluated'}"
# templating: on
evaluated = "${'WILL get evaluated'}"

becomes

example = "${'will NOT get evaluated'}"
evaluated = "WILL get evaluated"
```
