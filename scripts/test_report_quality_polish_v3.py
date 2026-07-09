from reporting.task2.renderers.daily_social_media_report_renderer import RENDER_PACKAGE_VERSION as DAILY_VERSION
from reporting.task2.renderers.mainstream_media_report_renderer import RENDER_PACKAGE_VERSION as MMR_VERSION
from reporting.task2.workflows.mainstream_media_report_workflow import _effective_issue_target

print("DAILY_VERSION =", DAILY_VERSION)
print("MMR_VERSION =", MMR_VERSION)
print("MMR_TARGET_46 =", _effective_issue_target(46, 0.10, 50, 150))
print("MMR_TARGET_830 =", _effective_issue_target(830, 0.10, 50, 150))
assert DAILY_VERSION == "daily_social_report_render_package_v4"
assert MMR_VERSION == "mainstream_media_report_render_package_v3"
assert _effective_issue_target(46, 0.10, 50, 150) == 46
assert _effective_issue_target(83, 0.10, 50, 150) == 83
assert _effective_issue_target(830, 0.10, 50, 150) == 83
print("REPORT QUALITY POLISH V3 OK")
