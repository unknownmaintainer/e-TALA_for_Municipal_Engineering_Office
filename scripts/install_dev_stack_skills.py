import os
import shutil

source_dir = r"c:\Users\Dion\Desktop\eTala\Dev-Stack-Agents-main\Dev-Stack-Agents-main"
target_base_dir = r"c:\Users\Dion\Desktop\eTala\.agents\skills"

os.makedirs(target_base_dir, exist_ok=True)

installed_count = 0
for filename in os.listdir(source_dir):
    if filename.endswith(".md") and filename not in ["README.md", "LICENSE"]:
        agent_name = filename[:-3]  # remove .md
        agent_skill_dir = os.path.join(target_base_dir, agent_name)
        os.makedirs(agent_skill_dir, exist_ok=True)
        
        src_path = os.path.join(source_dir, filename)
        dst_path = os.path.join(agent_skill_dir, "SKILL.md")
        
        shutil.copy2(src_path, dst_path)
        installed_count += 1
        print(f"Installed skill: {agent_name} -> {dst_path}")

print(f"\nSuccessfully installed {installed_count} Dev-Stack skills into .agents/skills/")
