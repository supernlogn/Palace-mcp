# [Overview](#Overview)[]()[](#Overview)

A configuration file written in the [JSON format](https://en.wikipedia.org/wiki/JSON) is used specify the runtime options for a *Palace* simulation. The following sections give a detailed overview of the file format and available settings.

Parameters are specified in the form of keyword/value pairs where the key is a string and the value may be a string, boolean, integer or floating point number, or array. Parameters are grouped into a hierarchy of objects. We support relaxed JSON formatting with C++-style comments (`//`, `/* */`). Integer arrays can be specified as comma-separated lists of integers or integer ranges, for example `[1,3-5,6]` is parsed as `[1,3,4,5,6]`.

In the following sections, default values for the parameters are specified alongside the description of each keyword in square brackets. Keywords for which there is no default value listed (`[None]`) are required in general if specifying values for other keywords under the same top-level object.

The top-level JSON object of the configuration file has the following structure:

```
{
    "Problem":
    {
        ...
    },
    "Model":
    {
        ...
    },
    "Domains":
    {
        ...
    },
    "Boundaries":
    {
        ...
    },
    "Solver":
    {
        ...
    }
}
```

Each property of the top-level `config` JSON object is detailed in its corresponding section of the documentation.

## [Contents](#Contents)[]()[](#Contents)

- [`config["Problem"]`](../problem/)
- [`config["Model"]`](../model/)
- [`config["Domains"]`](../domains/)
- [`config["Boundaries"]`](../boundaries/)
- [`config["Solver"]`](../solver/)
