class PrintA11y:
    def __init__(self):
        self.alts = []
        self.collected = []
        self.last_strings = []
        self.inhibit = False
        self.process = None

    def add_alt(self, app, text, always=False, transient=False):
        if not self.inhibit:
            self.alts.append((text, always, transient))

    def collect_text(self, text):
        if not self.inhibit:
            self.collected.append(text)

    def reset(self):
        self.collected = []
        self.alts = []

    def get_all_strings(self):
        if self.alts:
            return [s for (s, a, t) in self.alts]
        return self.collected

    def get_deduped_strings(self):
        if self.alts:
            strings = self.alts
        else:
            strings = [(s, False, False) for s in self.collected]
        if self.last_strings == strings:
            return

        has_transients = False
        output_strings = []
        has_transients = any(t for (s, a, t) in strings)
        for i, (string, always, transient) in enumerate(strings):
            if transient:
                output_strings.append(string)
            elif always:
                output_strings.append(string)
            elif (
                not has_transients
                and len(self.last_strings) > i
                and self.last_strings[i][0] != string
            ):
                output_strings.append(string)

        self.last_strings = strings
        return output_strings

    async def finalise_frame(self):
        text = self.get_deduped_strings()
        if text:
            print("[Screen reader] " + " ".join(text))


_printa11y = PrintA11y()
