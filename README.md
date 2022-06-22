<!--- Top of README Badges (automated) --->
[![GitHub release (latest by date including pre-releases)](https://img.shields.io/github/v/release/icecube/skymap_scanner?include_prereleases)](https://github.com/icecube/skymap_scanner/) [![Lines of code](https://img.shields.io/tokei/lines/github/icecube/skymap_scanner)](https://github.com/icecube/skymap_scanner/) [![GitHub issues](https://img.shields.io/github/issues/icecube/skymap_scanner)](https://github.com/icecube/skymap_scanner/issues?q=is%3Aissue+sort%3Aupdated-desc+is%3Aopen) [![GitHub pull requests](https://img.shields.io/github/issues-pr/icecube/skymap_scanner)](https://github.com/icecube/skymap_scanner/pulls?q=is%3Apr+sort%3Aupdated-desc+is%3Aopen) 
<!--- End of README Badges (automated) --->
# skymap_scanner

Distributed likelihood scan of event directions for real-time alerts.
This is a set of scripts meant to be deployed as containers.

Top level is the icetray project intended to actually perform the scan. 

This was copied over from Subversion on Dec 11, 2021 by E. Blaufuss
https://code.icecube.wisc.edu/projects/icecube/browser/IceCube/sandbox/ckopper/skymap_scanner?rev=185232

Also includes cloud_tools to manage event distribution in cloud settings
see skymap_scanner/cloud_tools
