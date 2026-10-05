# -*- coding: utf-8 -*-
"""qoder 流水线自动补位监视器
逻辑：保持 12 路 qoderclicn 并发；切片完成后自动启动下一个未派发的切片；
全部 31 片派发完毕且无活跃进程后退出。
"""
import os, time, json, subprocess, sys, re

ROOT = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(ROOT, "_batches", "watcher_state.json")
LOGDIR = os.path.join(ROOT, "_batches")
CONCURRENCY = 12
TOTAL_SLICES = 21
QODER = "qoderclicn"

def load_state():
    if os.path.exists(STATE):
        return json.load(open(STATE, encoding="utf-8"))
    return {"launched": {}}

def save_state(st):
    json.dump(st, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

def active_slices():
    """数当前活跃的 task_q* 进程数（PowerShell CIM，wmic 已在此系统移除）"""
    active = set()
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command",
            "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*task_q*' } | "
            "Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"],
            capture_output=True, text=True, timeout=90)
        txt = out.stdout.strip()
        if txt:
            data = json.loads(txt)
            if isinstance(data, dict):
                data = [data]
            for p in data:
                m = re.search(r"task_q(\d+)\.md", p.get("CommandLine") or "")
                if m:
                    active.add(int(m.group(1)))
    except Exception as e:
        print("进程扫描异常:", e)
    return active

def main():
    st = load_state()
    launched = st.setdefault("launched", {})
    print(f"监视器启动：并发={CONCURRENCY}，总切片={TOTAL_SLICES}，已派发={len(launched)}")
    idle_rounds = 0
    while True:
        active = active_slices()
        st = load_state()
        launched = st.setdefault("launched", {})
        # 补位：找未派发的切片
        launched_now = []
        for n in range(1, TOTAL_SLICES + 1):
            if len(active) + len(launched_now) >= CONCURRENCY:
                break
            s = str(n)
            if s not in launched:
                log = os.path.join(LOGDIR, f"run_q{n}.log")
                cmd = f'{QODER} chat -p "读取 _batches/task_q{n}.md 并严格执行全部任务" -m Qwen3.8-Flash --permission-mode bypass_permissions --cwd "{ROOT}"'
                subprocess.Popen(cmd, shell=True, stdout=open(log, "ab"),
                                 stderr=subprocess.STDOUT, cwd=ROOT)
                launched[s] = {"launched_at": time.strftime("%H:%M:%S")}
                launched_now.append(n)
                active.add(n)
                print(f"[{time.strftime('%H:%M:%S')}] 启动切片 q{n}")
        if launched_now:
            save_state(st)
        done_all = len(launched) >= TOTAL_SLICES
        if done_all and len(active) == 0:
            print("全部切片完成且无活跃进程，监视器退出")
            break
        # 长时间无变化时打印心跳
        print(f"[{time.strftime('%H:%M:%S')}] 活跃={len(active)} 已派发={len(launched)}/{TOTAL_SLICES}", flush=True)
        time.sleep(240)

if __name__ == "__main__":
    main()
