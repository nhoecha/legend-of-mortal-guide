# 이미 열려 있는 브라우저 창을 찾아 새로고침한다.
# 결과 파일을 고칠 때마다 Start-Process 로 새로 열면 탭이 계속 쌓인다(작성자 요청, 2026-09-01).
#
#   .\refresh-page.ps1                     제목에 '활협전' 이 든 창을 새로고침
#   .\refresh-page.ps1 -Title '보고서'      다른 창
#   .\refresh-page.ps1 -OpenIfMissing      창을 못 찾으면 그때만 새로 연다
#
# 찾지 못하면 종료 코드 1 을 낸다. 부르는 쪽이 그때만 새로 열면 된다.

param(
    # '활협전' 은 run.bat 을 돌리는 cmd 창에도 걸린다. 브라우저 창만 잡도록 '도감' 을 쓴다.
    [string]$Title = '도감',
    [string]$Path = (Join-Path (Split-Path $PSScriptRoot -Parent) '활협전-도감.html'),
    [switch]$OpenIfMissing
)

$sig = @'
using System;
using System.Text;
using System.Collections.Generic;
using System.Runtime.InteropServices;
public class WinRefresh {
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc cb, IntPtr l);
  public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
  [DllImport("user32.dll")] public static extern int GetWindowTextLength(IntPtr h);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int cmd);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  public static List<KeyValuePair<IntPtr,string>> All() {
    var r = new List<KeyValuePair<IntPtr,string>>();
    EnumWindows(delegate(IntPtr h, IntPtr l) {
      if (!IsWindowVisible(h)) return true;
      int len = GetWindowTextLength(h);
      if (len == 0) return true;
      var sb = new StringBuilder(len + 1);
      GetWindowText(h, sb, sb.Capacity);
      r.Add(new KeyValuePair<IntPtr,string>(h, sb.ToString()));
      return true;
    }, IntPtr.Zero);
    return r;
  }
}
'@
if (-not ([System.Management.Automation.PSTypeName]'WinRefresh').Type) {
    Add-Type -TypeDefinition $sig -Language CSharp
}
Add-Type -AssemblyName System.Windows.Forms

$hit = [WinRefresh]::All() | Where-Object { $_.Value -like "*$Title*" } | Select-Object -First 1

if (-not $hit) {
    if ($OpenIfMissing) {
        Start-Process $Path
        "열린 창이 없어 새로 열었다: $Path"
        exit 0
    }
    "제목에 '$Title' 이 든 창을 찾지 못했다."
    exit 1
}

$prev = [WinRefresh]::GetForegroundWindow()
[void][WinRefresh]::ShowWindow($hit.Key, 9)          # SW_RESTORE
[void][WinRefresh]::SetForegroundWindow($hit.Key)
Start-Sleep -Milliseconds 250
[System.Windows.Forms.SendKeys]::SendWait('{F5}')
Start-Sleep -Milliseconds 250
if ($prev -ne [IntPtr]::Zero) { [void][WinRefresh]::SetForegroundWindow($prev) }

"새로고침: $($hit.Value)"
