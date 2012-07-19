Sentry Defcon
=============

A sentry plugin that measures the current error throughput (globally) and show you
the current condition status using Defcon code (1 to 5 where 1 means war and 5 peace).

When Defcon 1 is reached you will get an email about it.


You can connect to the Defcon 1 is reached and define custom action (eg. send an sms, buy a plane ticket ...).


To subscribe to a signal you just need to define a callback and then connect it like this:


	from sentry_defcon import signals

	def press_the_red_button(sender):
		...

	signals.defcon_one_reached.connect(press_the_red_button)


Defcon levels are based on the setting errors received per period (eg. 10 per second).
When you are receiving 4 times the errors per period defined you are in Defcon 2 and Defcon 1 when 5 or more times than that.

Defcon 1 status will be kept for an amount of seconds you can define in the setting screen (cooldown period).

At this present this plugin requires my forked version of Sentry, you can grab it from [here](https://github.com/tbarbugli/sentry).
Note that you need to run `sentry --config=config upgrade` command if you switch to this verions.