class PrintA11y:
    def __init__(self):
        self.alts = []
        self._cached_alt = None
        self.collected = []
        self.last_strings = []
        self._last_strings_are_alts = False
        self._collect_has_transients = False
        self.inhibit = False
        self.process = None

    def add_alt(self, app, text, always=False, transient=False):
        if not self.inhibit:
            cached_alt = self._cached_alt
            if (
                cached_alt is None
                or cached_alt[0] != text
                or cached_alt[1] != always
                or cached_alt[2] != transient
            ):
                cached_alt = (text, always, transient)
                self._cached_alt = cached_alt
            self.alts.append(cached_alt)

    def collect_text(self, text):
        if not self.inhibit:
            self.collected.append(text)

    def reset(self):
        self.collected.clear()
        self.alts.clear()

    def get_all_strings(self):
        if self.alts:
            return [s for (s, a, t) in self.alts]
        return self.collected

    def get_deduped_strings(self):
        use_alts = bool(self.alts)
        strings = self.alts if use_alts else self.collected
        if self._strings_unchanged(strings, use_alts):
            return
        return self._collect_changed_strings(strings, use_alts)

    def _strings_unchanged(self, strings, use_alts):
        return self._last_strings_are_alts == use_alts and self.last_strings == strings

    def _collect_changed_strings(self, strings, use_alts):
        self._collect_has_transients = self._has_transient_strings(strings, use_alts)
        output_strings = self._collect_string_entries(strings)
        self.last_strings = strings[:]
        self._last_strings_are_alts = use_alts
        return output_strings

    def _collect_string_entries(self, strings):
        use_alts = strings is self.alts
        output_strings = []
        index = 0
        while index < len(strings):
            entry = self._string_entry(strings, use_alts, index)
            if self._should_emit_string(entry, index, use_alts):
                output_strings.append(entry[0] if use_alts else entry)
            index += 1
        return output_strings

    def _should_emit_string(self, entry, index, use_alts):
        if use_alts:
            string, always, transient = entry
            if transient or always:
                return True
        else:
            string = entry
        return (
            not self._collect_has_transients
            and len(self.last_strings) > index
            and self._last_string_text(index) != string
        )

    def _has_transient_strings(self, strings, use_alts):
        if not use_alts:
            return False
        index = 0
        while index < len(strings):
            if strings[index][2]:
                return True
            index += 1
        return False

    def _string_entry(self, strings, use_alts, index):
        if use_alts:
            return strings[index]
        return strings[index]

    def _last_string_text(self, index):
        if self._last_strings_are_alts:
            return self.last_strings[index][0]
        return self.last_strings[index]

    async def finalise_frame(self):
        text = self.get_deduped_strings()
        if text:
            print("[Screen reader] " + " ".join(text))


_printa11y = PrintA11y()
