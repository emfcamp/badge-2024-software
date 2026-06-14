class Inhibitor:
    def __init__(self, a11y, val):
        self.a11y = a11y
        self.val = val

    def __enter__(self):
        if self.a11y:
            self.a11y.inhibit = self.val

    def __exit__(self, exc_type, exc_value, exc_tb):
        if self.a11y:
            self.a11y.inhibit = False


class A11yImplementation:
    def inhibit(self):
        pass

    def collect(self, val):
        pass

    def add_alt(self, app, text, always=False, transient=False):
        pass

    def collect_text(self, text):
        pass

    def reset(self):
        pass

    def get_all_strings(self):
        pass

    def get_deduped_strings(self):
        return
