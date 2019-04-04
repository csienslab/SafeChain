SAFECHAIN: Securing Trigger-Action Programming from Attack Chains
==

Dependencies
--
* [NuSMV](http://nusmv.fbk.eu/): make sure the `NuSMV` executable is in your PATH.
* Python3 package: `networkx`

Example
--
[example.py](example.py) gives an example of how to check privacy leakage for
the following scenario:
* The automation rule set to be "When get home, turn on the Hue light."
* Attackers can observe the state of the light.
* Users would like to prevent attackers from knowing whether they are at home or not.
