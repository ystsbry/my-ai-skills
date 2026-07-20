.PHONY: install-claudecode uninstall-claudecode \
	install-codex uninstall-codex install-codex-skills uninstall-codex-skills

# Override the dir with `make install-claudecode CLAUDE_SKILLS_DIR=/path`.
CLAUDE_SKILLS_DIR ?= $(HOME)/.claude/skills
PLUGIN_NAME := ybaba
PLUGIN_SRC := $(CURDIR)/plugin

AGENTS_HOME ?= $(HOME)/.agents
CODEX_SKILLS_DIR := $(AGENTS_HOME)/skills
CODEX_SKILLS_SRC := $(CURDIR)/plugin/skills

# Symlink plugin/ into ~/.claude/skills/ybaba so Claude Code auto-loads it
# as a skills-dir plugin. Restart claude, then verify with `claude plugin list`.
install-claudecode:
	@mkdir -p $(CLAUDE_SKILLS_DIR)
	@target=$(CLAUDE_SKILLS_DIR)/$(PLUGIN_NAME); \
	if [ -L $$target ]; then \
		rm -f $$target; \
	elif [ -e $$target ]; then \
		echo "skip: $$target already exists (not a symlink)"; \
		exit 0; \
	fi; \
	ln -s $(PLUGIN_SRC) $$target; \
	echo "Linked $$target -> $(PLUGIN_SRC)"

uninstall-claudecode:
	@target=$(CLAUDE_SKILLS_DIR)/$(PLUGIN_NAME); \
	if [ -L $$target ]; then \
		rm -f $$target; \
		echo "Removed $$target"; \
	fi

# Register the same plugin/ with Codex via the local marketplace
# (.agents/plugins/marketplace.json). Codex COPIES the plugin into
# ~/.codex/plugins/cache/, so re-install after editing SKILL.md files.
install-codex:
	codex plugin marketplace add $(CURDIR)
	@echo "Added marketplace '$(PLUGIN_NAME)'. Verify/enable with 'codex plugin', then restart codex."

uninstall-codex:
	-codex plugin marketplace remove $(PLUGIN_NAME)

# Fallback for codex versions without plugin support: per-skill DIRECTORY
# symlinks into ~/.agents/skills ($<skill-name>). Codex's skill loader follows
# directory symlinks but drops symlinked SKILL.md files (openai/codex#15756).
# Live-edits apply immediately, unlike the marketplace copy.
install-codex-skills:
	@mkdir -p $(CODEX_SKILLS_DIR)
	@for src in $(CODEX_SKILLS_SRC)/*/; do \
		name=$$(basename $$src); \
		target=$(CODEX_SKILLS_DIR)/$$name; \
		if [ -L $$target ]; then \
			rm -f $$target; \
		elif [ -e $$target ]; then \
			echo "skip: $$target already exists (not a symlink)"; \
			continue; \
		fi; \
		ln -s $${src%/} $$target; \
		echo "Linked $$target -> $${src%/}"; \
	done

uninstall-codex-skills:
	@for src in $(CODEX_SKILLS_SRC)/*/; do \
		name=$$(basename $$src); \
		target=$(CODEX_SKILLS_DIR)/$$name; \
		if [ -L $$target ]; then \
			rm -f $$target; \
			echo "Removed $$target"; \
		fi; \
	done
