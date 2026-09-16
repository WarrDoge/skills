#!/bin/sh
# Installs git-hook as the global core.hooksPath; --uninstall reverts it.
set -eu

dir=${XDG_CONFIG_HOME:-$HOME/.config}/git/hooks
# reference-transaction and post-index-change are left out: they fire on every
# ref update or index write, and chaining them would slow down all repos.
hooks='applypatch-msg pre-applypatch post-applypatch pre-commit pre-merge-commit
prepare-commit-msg commit-msg post-commit pre-rebase post-checkout post-merge
pre-push pre-receive update proc-receive post-receive post-update
push-to-checkout pre-auto-gc post-rewrite sendemail-validate'
current=$(git config --global --get core.hooksPath || true)

if [ "${1:-}" = --uninstall ]; then
	[ "$current" != "$dir" ] || git config --global --unset core.hooksPath
	for h in $hooks; do
		[ "$(readlink "$dir/$h" 2>/dev/null)" != ai-attribution ] || rm "$dir/$h"
	done
	rm -f "$dir/ai-attribution"
	rmdir "$dir" 2>/dev/null || true
	echo "uninstalled"
	exit
fi

if [ -n "$current" ] && [ "$current" != "$dir" ]; then
	echo "core.hooksPath is already $current; not overriding it" >&2
	exit 1
fi

mkdir -p "$dir"
cp "$(dirname "$0")/git-hook" "$dir/ai-attribution"
chmod 755 "$dir/ai-attribution"
for h in $hooks; do
	if [ -e "$dir/$h" ] && [ "$(readlink "$dir/$h" 2>/dev/null)" != ai-attribution ]; then
		echo "skipping $dir/$h: not ours" >&2
		continue
	fi
	ln -sf ai-attribution "$dir/$h"
done
git config --global core.hooksPath "$dir"
echo "installed: core.hooksPath=$dir"
