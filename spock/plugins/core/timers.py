import time
from spock.mcp import mcdata
from spock.utils import pl_announce

class BaseTimer(object):
	def __init__(self, callback, runs = 1):
		self.callback = callback
		self.runs = runs

	def get_runs(self):
		return self.runs

	def update(self):
		if self.check():
			self.fire()

	def fire(self):
		self.callback()
		if self.runs>0:
			self.runs-=1
		if self.runs:
			self.reset()

	def stop(self):
		self.runs = 0

#Time based timer
class EventTimer(BaseTimer):
	def __init__(self, wait_time, callback, runs = 1):
		super().__init__(callback, runs)
		self.wait_time = wait_time
		self.end_time = time.time() + self.wait_time

	def countdown(self):
		count = self.end_time - time.time()
		return count if count > 0 else 0


	def check(self):
		if self.runs == 0: return False
		return self.end_time<=time.time()

	def reset(self):
		self.end_time = time.time() + self.wait_time

#World tick based timer
class TickTimer(BaseTimer):
	def __init__(self, world, wait_ticks, callback, runs = 1):
		super().__init__(callback, runs)
		self.world = world
		self.wait_ticks = wait_ticks
		self.end_tick = self.world.age + self.wait_ticks

	def countdown(self):
		return -1

	def check(self):
		if self.runs == 0: return False
		return self.end_tick<=self.world.age

	def reset(self):
		self.end_tick = self.world.age + self.wait_ticks

class TimerCore:
	def __init__(self, world):
		self.timers = []
		self.world = world

	def reg_timer(self, timer):
		self.timers.append(timer)

	def get_timeout(self):
		timeout = -1
		for timer in self.timers:
			if timeout > timer.countdown() or timeout == -1:
					timeout = timer.countdown()
		return timeout

	def reg_event_timer(self, wait_time, callback, runs = 1):
		self.reg_timer(EventTimer(wait_time, callback, runs))

	def reg_tick_timer(self, wait_ticks, callback, runs = 1):
		self.reg_timer(TickTimer(self.world, wait_ticks, callback, runs))

class WorldTick:
	def __init__(self):
		self.age = 0

@pl_announce('Timers')
class TimerPlugin:
	def __init__(self, ploader, settings):
		self.world = ploader.requires('World')
		if not self.world:
			self.world = WorldTick()
			ploader.reg_event_handler(
				(mcdata.PLAY_STATE, mcdata.SERVER_TO_CLIENT, 0x03), 
				self.handle03
			)
		self.timer_core = TimerCore(self.world)
		ploader.provides('Timers', self.timer_core)
		ploader.reg_event_handler('tick', self.tick)
		ploader.reg_event_handler('SOCKET_ERR', self.handle_disconnect)
		ploader.reg_event_handler('SOCKET_HUP', self.handle_disconnect)

	def tick(self, name, data):
		for timer in self.timer_core.timers:
			timer.update()
			if not timer.get_runs():
				self.timer_core.timers.remove(timer)

	#Time Update - We grab world age if the world plugin isn't available
	def handle03(self, name, packet):
		self.world.age = packet.data['world_age']

	def handle_disconnect(self, name, data):
		self.timer_core.timers = []