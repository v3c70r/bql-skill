#!/bin/sh
# install.sh — Cross-platform BQL Skill installer
# POSIX-compatible. Installs to native paths for 15+ platforms.
#
# Usage:
#   ./install.sh                    # Auto-detect platform and install
#   ./install.sh --platform claude  # Install for specific platform
#   ./install.sh --all              # Install to all detected platforms
#   ./install.sh --dry-run          # Show what would be installed
#   ./install.sh --uninstall        # Remove from all platforms

set -eu

SKILL_NAME="bql-query-skill"
SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"

# Colors
if [ -t 1 ]; then
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
    BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'
else
    RED=''; GREEN=''; YELLOW=''; BLUE=''; BOLD=''; NC=''
fi

info()    { printf "${BLUE}[INFO]${NC}  %s\n" "$1"; }
success() { printf "${GREEN}[OK]${NC}    %s\n" "$1"; }
warn()    { printf "${YELLOW}[WARN]${NC}  %s\n" "$1"; }
error()   { printf "${RED}[ERROR]${NC} %s\n" "$1" >&2; }

# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------
detect_platforms() {
    DETECTED=""
    [ -d "$HOME/.claude" ]            && DETECTED="$DETECTED claude"
    [ -d "$HOME/.copilot" ]           && DETECTED="$DETECTED copilot"
    [ -d ".github" ]                  && DETECTED="$DETECTED github-copilot"
    [ -d ".cursor" ]                  && DETECTED="$DETECTED cursor"
    [ -d "$HOME/.codeium/windsurf" ]  && DETECTED="$DETECTED windsurf-global"
    [ -d ".windsurf" ]                && DETECTED="$DETECTED windsurf-project"
    [ -d ".clinerules" ]              && DETECTED="$DETECTED cline"
    [ -d "$HOME/.cline" ]             && DETECTED="$DETECTED cline-global"
    [ -d "$HOME/.gemini" ]            && DETECTED="$DETECTED gemini"
    [ -d "$HOME/.config/goose" ]      && DETECTED="$DETECTED goose"
    [ -d "$HOME/.config/opencode" ]   && DETECTED="$DETECTED opencode"
    [ -d "$HOME/.roo" ]               && DETECTED="$DETECTED roo-code"
    [ -d "$HOME/.agents" ]            && DETECTED="$DETECTED universal"
    printf "%s" "$DETECTED"
}

get_platform_path() {
    case "$1" in
        claude)          echo "$HOME/.claude/skills/$SKILL_NAME" ;;
        copilot)         echo "$HOME/.copilot/skills/$SKILL_NAME" ;;
        github-copilot)  echo "$(pwd)/.github/skills/$SKILL_NAME" ;;
        cursor)          echo "$(pwd)/.cursor/skills/$SKILL_NAME" ;;
        windsurf-global) echo "$HOME/.codeium/windsurf/skills/$SKILL_NAME" ;;
        windsurf-project)echo "$(pwd)/.windsurf/rules/$SKILL_NAME" ;;
        cline)           echo "$(pwd)/.clinerules/skills/$SKILL_NAME" ;;
        cline-global)    echo "$HOME/.cline/skills/$SKILL_NAME" ;;
        gemini)          echo "$HOME/.gemini/skills/$SKILL_NAME" ;;
        goose)           echo "$HOME/.config/goose/skills/$SKILL_NAME" ;;
        opencode)        echo "$HOME/.config/opencode/skills/$SKILL_NAME" ;;
        roo-code)        echo "$HOME/.roo/skills/$SKILL_NAME" ;;
        universal)       echo "$HOME/.agents/skills/$SKILL_NAME" ;;
        pi)              echo "$HOME/.pi/agent/skills/$SKILL_NAME" ;;
        *)               echo "" ;;
    esac
}

install_platform() {
    platform="$1"
    target="$(get_platform_path "$platform")"
    if [ -z "$target" ]; then
        warn "Unknown platform: $platform"
        return 1
    fi

    parent="$(dirname "$target")"
    mkdir -p "$parent"

    if [ -d "$target" ] || [ -L "$target" ]; then
        warn "Already installed at $target — replacing"
        rm -rf "$target"
    fi

    cp -R "$SKILL_DIR" "$target"
    # Remove .git directory from installed copy to keep it lightweight
    rm -rf "$target/.git" 2>/dev/null || true
    success "Installed to $target"
}

uninstall_platform() {
    platform="$1"
    target="$(get_platform_path "$platform")"
    if [ -z "$target" ]; then
        return 1
    fi
    if [ -d "$target" ] || [ -L "$target" ]; then
        rm -rf "$target"
        success "Removed $target"
    fi
}

print_activation() {
    echo ""
    echo "${BOLD}Skill installed successfully!${NC}"
    echo ""
    echo "To use it, open a new session and type:"
    echo ""
    echo "  ${GREEN}/bql-query-skill${NC} How much did I spend on food last month?"
    echo ""
    echo "Or ask naturally:"
    echo ""
    echo "  Query my Beancount ledger for restaurant expenses in Q1"
    echo ""
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
DRY_RUN=false
ALL=false
UNINSTALL=false
TARGET_PLATFORM=""

while [ $# -gt 0 ]; do
    case "$1" in
        --platform) TARGET_PLATFORM="$2"; shift 2 ;;
        --all)      ALL=true; shift ;;
        --dry-run)  DRY_RUN=true; shift ;;
        --uninstall) UNINSTALL=true; shift ;;
        -h|--help)
            echo "Usage: ./install.sh [options]"
            echo ""
            echo "Options:"
            echo "  --platform <name>  Install for specific platform"
            echo "  --all              Install to all detected platforms"
            echo "  --dry-run          Show what would be installed"
            echo "  --uninstall        Remove from all platforms"
            echo "  -h, --help         Show this help"
            echo ""
            echo "Platforms: claude, copilot, github-copilot, cursor,"
            echo "           windsurf-global, windsurf-project, cline,"
            echo "           cline-global, gemini, goose, opencode,"
            echo "           roo-code, universal, pi"
            exit 0
            ;;
        *) error "Unknown option: $1"; exit 1 ;;
    esac
done

echo "${BOLD}BQL Query Skill Installer${NC}"
echo ""

# Validate SKILL.md exists
if [ ! -f "$SKILL_DIR/SKILL.md" ]; then
    error "SKILL.md not found in $SKILL_DIR"
    exit 1
fi

PLATFORMS="$(detect_platforms)"

if [ "$UNINSTALL" = true ]; then
    for p in $PLATFORMS pi; do
        uninstall_platform "$p" 2>/dev/null || true
    done
    echo "Uninstall complete."
    exit 0
fi

if [ "$DRY_RUN" = true ]; then
    echo "Would install to:"
    for p in $PLATFORMS; do
        target="$(get_platform_path "$p")"
        echo "  $p → $target"
    done
    echo "  pi → $HOME/.pi/agent/skills/$SKILL_NAME"
    exit 0
fi

if [ -n "$TARGET_PLATFORM" ]; then
    install_platform "$TARGET_PLATFORM"
else
    if [ -z "$PLATFORMS" ]; then
        warn "No platforms detected. Installing to universal path."
        PLATFORMS="universal"
    fi

    if [ "$ALL" = true ]; then
        for p in $PLATFORMS; do
            install_platform "$p"
        done
    else
        # Install to first detected platform
        FIRST="$(echo "$PLATFORMS" | awk '{print $1}')"
        install_platform "$FIRST"
    fi
fi

# Always install to universal path
install_platform "universal" 2>/dev/null || true

print_activation
