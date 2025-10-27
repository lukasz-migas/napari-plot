import sys
from inspect import Parameter, getdoc, signature

import napari.utils._register
from napari.utils._register import template
from napari.utils.misc import camel_to_snake


def create_func(cls, name=None, doc=None, filename: str = "<string>"):
    cls_name = cls.__name__

    if name is None:
        name = camel_to_snake(cls_name)

    if "layer" in name:
        raise ValueError(f"name {name} should not include 'layer'")

    name = "add_" + name

    if doc is None:
        doc = getdoc(cls)
        cutoff = doc.find("\n\nParameters\n----------\n")
        if cutoff > 0:
            doc = doc[cutoff:]

        n = "n" if cls_name[0].lower() in "aeiou" else ""
        doc = f"Add a{n} {cls_name} layer to the layer list. " + doc
        doc += "\n\nReturns\n-------\n"
        doc += f"layer : :class:`napari.layers.{cls_name}`"
        doc += f"\n\tThe newly-created {cls_name.lower()} layer."
        doc = doc.expandtabs(4)

    sig = signature(cls)
    new_sig = sig.replace(
        parameters=[Parameter("self", Parameter.POSITIONAL_OR_KEYWORD)] + list(sig.parameters.values()),
        return_annotation=cls,
    )
    src = template.format(
        name=name,
        signature=new_sig,
        cls_name=cls_name,
    )

    execdict = {
        cls_name: cls,
        "napari": sys.modules.get("napari"),
        "napari_plot": sys.modules.get("napari_plot"),
    }
    code = compile(src, filename=filename, mode="exec")
    exec(code, execdict)
    func = execdict[name]

    func.__doc__ = doc

    func.__doc__ = doc

    return func


napari.utils._register.create_func = create_func
