"""Unit tests for the zsh half of ``songbook install-completion``.

Background: the original installer wrote ``~/.songbook-complete.zsh`` and
appended a ``source`` line to ``.zshrc``. That registers the completion with
``compdef`` — and any ``compinit`` that runs *later* in ``.zshrc`` (installers
for other tools routinely append one) rebuilds ``_comps`` from scratch and
silently drops the registration. Completion then stops working with no error.

The durable shape is the one ``git``/``kubectl``/``deno`` use: a file named
``_<command>`` on ``fpath``, which every ``compinit`` rediscovers. These tests
pin that behavior, plus the cache invalidation it requires.

All tests run against a throwaway ``home`` directory — never the real one.
"""

from __future__ import annotations

import pytest

from cli.main import _install_zsh_completion

SCRIPT = "#compdef songbook\n_songbook_completion() { : }\n"


@pytest.fixture()
def home(tmp_path):
    (tmp_path / ".zshrc").write_text("# existing config\n", encoding="utf-8")
    return tmp_path


class TestInstallsOnFpath:
    def test_writes_the_completion_as_an_autoloaded_function(self, home):
        _install_zsh_completion(SCRIPT, home)

        installed = home / ".zsh" / "completions" / "_songbook"
        assert installed.read_text(encoding="utf-8") == SCRIPT

    def test_puts_the_completions_directory_on_fpath(self, home):
        _install_zsh_completion(SCRIPT, home)

        zshrc = (home / ".zshrc").read_text(encoding="utf-8")
        assert "$HOME/.zsh/completions" in zshrc
        assert "fpath" in zshrc

    def test_fpath_entry_lands_before_any_existing_compinit(self, home):
        """compinit scans fpath — an entry added after it is never seen."""
        (home / ".zshrc").write_text(
            "source $ZSH/oh-my-zsh.sh\nautoload -Uz compinit && compinit -C\n",
            encoding="utf-8",
        )

        _install_zsh_completion(SCRIPT, home)

        # Comments are skipped — only real invocations order-constrain us.
        lines = [
            l for l in (home / ".zshrc").read_text(encoding="utf-8").splitlines()
            if not l.lstrip().startswith("#")
        ]
        fpath_line = next(i for i, l in enumerate(lines) if ".zsh/completions" in l)
        compinit_line = next(i for i, l in enumerate(lines) if "compinit" in l)
        assert fpath_line < compinit_line

    def test_is_idempotent(self, home):
        _install_zsh_completion(SCRIPT, home)
        first = (home / ".zshrc").read_text(encoding="utf-8")

        _install_zsh_completion(SCRIPT, home)

        assert (home / ".zshrc").read_text(encoding="utf-8") == first

    def test_leaves_an_existing_fpath_entry_alone(self, home):
        (home / ".zshrc").write_text(
            'fpath=("$HOME/.zsh/completions" $fpath)\n', encoding="utf-8"
        )

        _install_zsh_completion(SCRIPT, home)

        zshrc = (home / ".zshrc").read_text(encoding="utf-8")
        assert zshrc.count(".zsh/completions") == 1

    def test_creates_zshrc_when_absent(self, tmp_path):
        _install_zsh_completion(SCRIPT, tmp_path)

        assert ".zsh/completions" in (tmp_path / ".zshrc").read_text(encoding="utf-8")


class TestInvalidatesTheCompletionCache:
    def test_removes_stale_zcompdump_files(self, home):
        """`compinit -C` trusts the dump blindly; a stale one hides _songbook."""
        stale = home / ".zcompdump"
        host_specific = home / ".zcompdump-Some-Host-5.9"
        compiled = home / ".zcompdump-Some-Host-5.9.zwc"
        for path in (stale, host_specific, compiled):
            path.write_text("cached", encoding="utf-8")

        _install_zsh_completion(SCRIPT, home)

        assert not stale.exists()
        assert not host_specific.exists()
        assert not compiled.exists()

    def test_survives_a_missing_cache(self, home):
        _install_zsh_completion(SCRIPT, home)  # no zcompdump present

        assert (home / ".zsh" / "completions" / "_songbook").exists()


class TestRemovesTheLegacySourcedInstall:
    def test_deletes_the_old_script_and_its_source_line(self, home):
        legacy = home / ".songbook-complete.zsh"
        legacy.write_text(SCRIPT, encoding="utf-8")
        (home / ".zshrc").write_text(
            "# Songbook completion\n"
            f'[[ -f "{legacy}" ]] && source "{legacy}"\n'
            "export PATH=/usr/local/bin:$PATH\n",
            encoding="utf-8",
        )

        _install_zsh_completion(SCRIPT, home)

        zshrc = (home / ".zshrc").read_text(encoding="utf-8")
        assert ".songbook-complete.zsh" not in zshrc
        assert "export PATH=/usr/local/bin:$PATH" in zshrc
        assert not legacy.exists()

    def test_backs_up_zshrc_before_rewriting_it(self, home):
        legacy = home / ".songbook-complete.zsh"
        legacy.write_text(SCRIPT, encoding="utf-8")
        original = f'source "{legacy}"\n'
        (home / ".zshrc").write_text(original, encoding="utf-8")

        _install_zsh_completion(SCRIPT, home)

        assert (home / ".zshrc.songbook-backup").read_text(encoding="utf-8") == original
