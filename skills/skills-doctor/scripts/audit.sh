#!/usr/bin/env bash
# ==============================================================================
# Skills Doctor - 全系统 AI Agent 技能深度体检与治理诊断脚本
# ==============================================================================

set -e

BOLD="\033[1m"
GREEN="\033[32m"
BLUE="\033[34m"
YELLOW="\033[33m"
RED="\033[31m"
CYAN="\033[36m"
RESET="\033[0m"

echo -e "${BOLD}${CYAN}"
echo "============================================================"
echo "         🩺 Skills Doctor 全系统 Agent 技能深度体检          "
echo "============================================================"
echo -e "${RESET}"

HOST_PATHS=(
    "${HOME}/.agents/skills"
    "${HOME}/.claude/skills"
    "${HOME}/.codex/skills"
    "${HOME}/.zcode/skills"
    "${HOME}/.workbuddy/skills"
)

BROKEN_LINKS=()
BACKUP_ITEMS=()
MISSING_SKILL_MD=()
MISSING_INTERFACE=()
TOTAL_SKILLS_FOUND=0

for hpath in "${HOST_PATHS[@]}"; do
    echo -e "${BOLD}▶ 宿主目录:${RESET} ${CYAN}${hpath}${RESET}"
    if [ ! -d "${hpath}" ]; then
        echo -e "  ${YELLOW}• 未初始化或不存在，跳过${RESET}\n"
        continue
    fi

    local_count=0
    for item in "${hpath}"/*; do
        [ -e "${item}" ] || [ -L "${item}" ] || continue
        item_name="$(basename "${item}")"
        case "${item_name}" in
            .*|"#SyncVersion") continue ;;
        esac

        # 检查死链
        if [ -L "${item}" ] && [ ! -e "${item}" ]; then
            BROKEN_LINKS+=("${item}")
            echo -e "  ${RED}[✗ 失效死链]${RESET} ${item_name} -> $(readlink "${item}")"
            continue
        fi

        # 检查备份残留
        if [[ "${item_name}" == *.bak* ]] || [[ "${item_name}" == *.old* ]]; then
            BACKUP_ITEMS+=("${item}")
            echo -e "  ${YELLOW}[⚠ 备份残留]${RESET} ${item_name}"
            continue
        fi

        if [ -d "${item}" ]; then
            ((TOTAL_SKILLS_FOUND++)) || true
            ((local_count++)) || true

            if [ ! -f "${item}/SKILL.md" ]; then
                MISSING_SKILL_MD+=("${item}")
                echo -e "  ${YELLOW}[⚠ 缺失 SKILL.md]${RESET} ${item_name}"
            elif [ ! -f "${item}/agents/interface.yaml" ]; then
                MISSING_INTERFACE+=("${item}")
            fi
        fi
    done

    echo -e "  ${GREEN}✔ 该目录发现有效技能: ${local_count} 个${RESET}\n"
done

echo "============================================================"
echo -e "${BOLD}📋 Skills Doctor 综合诊断大盘:${RESET}"
echo -e "  • 📦 有效技能总量: ${GREEN}${TOTAL_SKILLS_FOUND}${RESET} 处挂载"
echo -e "  • 💔 失效软链 (Broken Symlinks): ${#BROKEN_LINKS[@]} 处"
echo -e "  • 🗑️  历史备份垃圾 (.bak* 残留): ${#BACKUP_ITEMS[@]} 处"
echo -e "  • ⚠️  缺失 SKILL.md 的目录: ${#MISSING_SKILL_MD[@]} 处"
echo -e "  • 📄 缺少 agents/interface.yaml 契约: ${#MISSING_INTERFACE[@]} 处"
echo "============================================================"

if [ ${#BROKEN_LINKS[@]} -gt 0 ] || [ ${#BACKUP_ITEMS[@]} -gt 0 ]; then
    echo -e "\n${BOLD}🛠️ 推荐执行清理命令:${RESET}"
    for item in "${BROKEN_LINKS[@]}"; do
        echo "  rm \"${item}\""
    done
    for item in "${BACKUP_ITEMS[@]}"; do
        echo "  rm -rf \"${item}\""
    done
fi
echo ""
