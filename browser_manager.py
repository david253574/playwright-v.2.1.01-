import os
import sys
import shutil
import time
import subprocess
from typing import Dict, List, Optional, Tuple, Any

STRIP_AUTOMATION_ARGS = [
    "--disable-field-trial-config",
    "--disable-background-networking",
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-breakpad",
    "--disable-features=AvoidUnnecessaryBeforeUnloadCheckSync,DestroyProfileOnBrowserClose,DialMediaRouteProvider,GlobalMediaControls,HttpsUpgrades,LensOverlay,MediaRouter,PaintHolding,ThirdPartyStoragePartitioning,BlockOriginHeaderModificationOnRedirect,AvoidCorsURLLoaderRestartOnRedirect,Translate,AutoDeElevate,OptimizationHints,NetworkTimeServiceQuerying,AimEnabled,msForceBrowserSignIn,msEdgeUpdateLaunchServicesPreferredVersion",
    "--force-color-profile=srgb",
    "--use-mock-keychain",
    "--disable-renderer-backgrounding",
    "--disable-hang-monitor",
    "--enable-automation",
    "--no-sandbox"
]

COMMON_STEALTH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-first-run",
    "--start-maximized"
]

BRAVE_EXTRA_ARGS = [
    "--no-default-browser-check",
    "--disable-features=BraveShields,BraveRewards,BraveWallet,BraveVPN,BraveNews,BraveSpeedreader",
    "--disable-brave-update",
    "--disable-brave-extension"
]

EDGE_EXTRA_ARGS = [
    "--disable-features=msForceBrowserSignIn,msEdgeUpdateLaunchServicesPreferredVersion,msEdgeHub,msEdgeSidebar"
]

def get_candidate_paths() -> Dict[str, List[str]]:
    """Returns candidate binary paths tailored to Windows or Linux."""
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA", r"C:\Users\Default\AppData\Local")
        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        return {
            "chrome": [
                os.path.join(program_files, "Google", "Chrome", "Application", "chrome.exe"),
                os.path.join(program_files_x86, "Google", "Chrome", "Application", "chrome.exe"),
                os.path.join(local_app_data, "Google", "Chrome", "Application", "chrome.exe"),
            ],
            "msedge": [
                os.path.join(program_files_x86, "Microsoft", "Edge", "Application", "msedge.exe"),
                os.path.join(program_files, "Microsoft", "Edge", "Application", "msedge.exe"),
                os.path.join(local_app_data, "Microsoft", "Edge", "Application", "msedge.exe"),
            ],
            "brave": [
                os.path.join(program_files, "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
                os.path.join(program_files_x86, "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
                os.path.join(local_app_data, "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
            ]
        }
    else:
        return {
            "chrome": [
                "/usr/bin/google-chrome",
                "/usr/bin/google-chrome-stable",
                "/usr/bin/chromium-browser",
                "/usr/bin/chromium",
                os.path.expanduser("~/.local/share/browsers/chrome/opt/google/chrome/google-chrome")
            ],
            "msedge": [
                "/usr/bin/microsoft-edge-stable",
                "/usr/bin/microsoft-edge",
                "/opt/microsoft/msedge/msedge",
                os.path.expanduser("~/.local/share/browsers/edge/opt/microsoft/msedge/msedge")
            ],
            "brave": [
                "/usr/bin/brave-browser",
                "/usr/bin/brave-browser-stable",
                "/opt/brave.com/brave/brave-browser",
                os.path.expanduser("~/.local/share/browsers/brave/opt/brave.com/brave/brave-browser")
            ]
        }

def cleanup_profile_locks(profile_dir: str):
    """Safely clears SingletonLock, SingletonCookie, and SingletonSocket."""
    if not profile_dir or not os.path.exists(profile_dir):
        return
    for item in os.listdir(profile_dir):
        if item.startswith("Singleton"):
            fp = os.path.join(profile_dir, item)
            try:
                if os.path.islink(fp) or os.path.isfile(fp):
                    os.unlink(fp)
                elif os.path.isdir(fp):
                    shutil.rmtree(fp, ignore_errors=True)
            except Exception:
                pass

def find_browser_binary(engine: str) -> Optional[str]:
    """Finds the actual executable path for a given browser engine on the system."""
    engine = engine.lower().strip()
    candidates = get_candidate_paths()
    paths = candidates.get(engine, [])
    for p in paths:
        if os.path.exists(p):
            if sys.platform == "win32" or os.access(p, os.X_OK):
                return p
    # Fallback to PATH search via shutil.which
    exe_names = {
        "chrome": ["chrome.exe", "google-chrome", "chrome", "google-chrome-stable"],
        "msedge": ["msedge.exe", "microsoft-edge", "msedge"],
        "brave": ["brave.exe", "brave-browser", "brave"]
    }
    for name in exe_names.get(engine, []):
        try:
            which_path = shutil.which(name)
            if which_path and os.path.exists(which_path):
                return which_path
        except Exception:
            pass
    return None

def get_available_engines() -> List[str]:
    """Returns a list of browser engines installed and usable on this system."""
    available = []
    for engine in ["chrome", "msedge", "brave"]:
        if find_browser_binary(engine):
            available.append(engine)
    if not available:
        # On Windows, channel='chrome' and channel='msedge' are standard Playwright channels
        if sys.platform == "win32":
            available = ["chrome", "msedge"]
        else:
            available.append("chrome")
    return available

def resolve_engine(engine_name: str, log_fn=print) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Resolves the requested engine into (resolved_engine_type, channel, executable_path).
    If the requested engine is unavailable, automatically falls back to chrome.
    """
    eng = (engine_name or "chrome").lower().strip()
    
    if eng in ["msedge", "edge"]:
        binary = find_browser_binary("msedge")
        if binary:
            return "msedge", "msedge", binary
        elif sys.platform == "win32":
            return "msedge", "msedge", None
        else:
            log_fn("[BrowserManager] Warning: Microsoft Edge binary not found. Falling back to Google Chrome.")
            eng = "chrome"

    if eng == "brave":
        binary = find_browser_binary("brave")
        if binary:
            return "brave", None, binary
        else:
            log_fn("[BrowserManager] Warning: Brave Browser binary not found. Falling back to Google Chrome.")
            eng = "chrome"

    # Default: Chrome
    chrome_bin = find_browser_binary("chrome")
    return "chrome", "chrome", chrome_bin

def get_launch_kwargs(
    engine: str = "chrome",
    user_data_dir: Optional[str] = None,
    headless: bool = False,
    permissions: Optional[List[str]] = None,
    extra_args: Optional[List[str]] = None,
    log_fn=print
) -> Tuple[Dict[str, Any], str]:
    """
    Generates the complete kwargs dictionary for p.chromium.launch_persistent_context.
    Tailors CLI flags specifically for Chrome, Microsoft Edge, or Brave.
    Returns (kwargs_dict, resolved_engine_name).
    """
    resolved_engine, channel, executable_path = resolve_engine(engine, log_fn=log_fn)
    
    args = list(COMMON_STEALTH_ARGS)
    if extra_args:
        args.extend(extra_args)

    if resolved_engine == "brave":
        args.extend(BRAVE_EXTRA_ARGS)
    elif resolved_engine == "msedge":
        args.extend(EDGE_EXTRA_ARGS)

    kwargs: Dict[str, Any] = {
        "headless": headless,
        "args": args,
        "ignore_default_args": STRIP_AUTOMATION_ARGS,
        "no_viewport": True
    }

    if user_data_dir:
        kwargs["user_data_dir"] = os.path.abspath(user_data_dir)

    if permissions:
        kwargs["permissions"] = permissions

    if executable_path and os.path.exists(executable_path):
        kwargs["executable_path"] = executable_path
    elif channel:
        kwargs["channel"] = channel

    log_fn(f"[BrowserManager] Resolved Engine: {resolved_engine.upper()} | Target: {executable_path or channel} | Headless: {headless}")
    return kwargs, resolved_engine

def launch_persistent_context_with_fallback(
    playwright_instance,
    engine: str = "chrome",
    fallback_engines: Optional[List[str]] = None,
    user_data_dir: Optional[str] = None,
    headless: bool = False,
    permissions: Optional[List[str]] = None,
    extra_args: Optional[List[str]] = None,
    log_fn=print
):
    """
    Launches a persistent browser context with automatic singleton lock cleanup
    and fallback to alternative engines (e.g. Edge -> Chrome) if launch fails.
    Returns (context, actual_resolved_engine).
    """
    if fallback_engines is None:
        fallback_engines = ["chrome"] if engine != "chrome" else ["msedge"]

    candidate_engines = [engine] + [e for e in fallback_engines if e != engine]
    last_err = None

    for eng in candidate_engines:
        for attempt in range(2):
            try:
                if user_data_dir:
                    cleanup_profile_locks(user_data_dir)
                kwargs, resolved_eng = get_launch_kwargs(
                    engine=eng,
                    user_data_dir=user_data_dir,
                    headless=headless,
                    permissions=permissions,
                    extra_args=extra_args,
                    log_fn=log_fn
                )
                context = playwright_instance.chromium.launch_persistent_context(**kwargs)
                return context, resolved_eng
            except Exception as e:
                last_err = e
                err_str = str(e).lower()
                if attempt == 0 and ("existing browser session" in err_str or "singleton" in err_str):
                    log_fn(f"[BrowserManager] Notice: Cleaning locks and retrying launch for {eng}...")
                    if user_data_dir:
                        cleanup_profile_locks(user_data_dir)
                    time.sleep(2.0)
                else:
                    log_fn(f"[BrowserManager] Failed to launch {eng}: {e}")
                    break  # Try next engine

    raise RuntimeError(f"All browser launch candidates failed. Last error: {last_err}")
