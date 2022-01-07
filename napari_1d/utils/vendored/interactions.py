import wrapt


class ReadOnlyWrapper(wrapt.ObjectProxy):
    """
    Disable item and attribute setting with the exception of  ``__wrapped__``.
    """

    def __setattr__(self, name, val):
        if name != "__wrapped__":
            raise TypeError(f"cannot set attribute {name}")

        super().__setattr__(name, val)

    def __setitem__(self, name, val):
        raise TypeError(f"cannot set item {name}")
