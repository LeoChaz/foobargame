from abc import ABC
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum, auto
import random
import re
import time

from numpy.random import choice

from settings import \
    CONFIG_GAME_SPEED, \
    CONFIG_LOG_DETAILS, \
    MAX_FOOBAR_SALE, \
    MAX_ROBOTS_END_GAME, \
    NB_ROBOTS_START_GAME, \
    COST_ROBOT, \
    NB_FOO_BUY


@dataclass
class DealerResult:
    new_robots_number: int = 0
    money            : int = 0
    items_to_remove  : list = None


class AvailableProduct(Enum):
    FOO    = auto()
    BAR    = auto()
    FOOBAR = auto()
    SALE   = auto()
    BUY    = auto()


def sleeper(activity_type):
    """
        Deal with the time that makes a robot to perform an activity
    """
    if activity_type   == AvailableProduct.FOO:
        time.sleep(1/CONFIG_GAME_SPEED)
    elif activity_type == AvailableProduct.BAR:
        time.sleep(random.uniform(0.5/CONFIG_GAME_SPEED, 2.5/CONFIG_GAME_SPEED))
    elif activity_type == AvailableProduct.FOOBAR:
        time.sleep(2/CONFIG_GAME_SPEED)
    elif activity_type == AvailableProduct.SALE:
        time.sleep(10/CONFIG_GAME_SPEED)
    else:
        # 0s to buy
        pass


def user_input(factories, input_text='Please pick an activity'):
    """
        Gamer input to pick an activity
    """
    try:
        pattern            = re.compile("^[0-4]")
        input_data         = input(f'{input_text} (0-{len(factories) - 1}): ')
        status             = re.fullmatch(pattern, input_data)
        if not status:
            return user_input(factories, 'Wrong input, please pick an activity')
        else:
            return int(input_data)
    except UnicodeDecodeError:
        return user_input(factories, 'Something went wrong, please pick an activity')


class Product(ABC):
    def __init__(self, serial_number):
        self.serial_number = serial_number
        self.name = ''

    def __str__(self):
        return f'Serial {self.serial_number} - {self.name}'


class Foo(Product):
    def __init__(self, serial_number):
        super().__init__(serial_number)
        self.name = 'foo'


class Bar(Product):
    def __init__(self, serial_number):
        super().__init__(serial_number)
        self.name = 'bar'


class Foobar(Product):
    def __init__(self, serial_number):
        super().__init__(serial_number)
        self.name = 'foobar'


class ProductionMaker(ABC):
    """
        Base class to make any kind of activity
    """
    def check_possible(self, available_items=None, current_money=0): pass
    def make(self, available_items=None, serial_number=0, current_money=0): pass


class FooMaker(ProductionMaker):
    """
        Used to make a foo
    """
    def check_possible(self, available_items=None, current_money=0):
        return True

    def make(self, available_items=None, serial_number=0, current_money=0):
        print('Robot is making foo')
        sleeper(AvailableProduct.FOO)
        print('Robot made a new foo')
        return Foo(serial_number)


class BarMaker(ProductionMaker):
    """
        Used to make a bar
    """
    def check_possible(self, available_items=None, money=0):
        return True

    def make(self, available_items=None, serial_number=0, current_money=0):
        print('Robot is making bar')
        sleeper(AvailableProduct.BAR)
        print('Robot made a new bar')
        return Bar(serial_number)


class FoobarMaker(ProductionMaker):
    """
        Used to make a foobar
    """
    def check_possible(self, available_items=None, current_money=0):
        if not available_items:
            available_items = []

        has_foo = any(x.name == "foo" for x in available_items)
        has_bar = any(x.name == "bar" for x in available_items)
        if has_foo and has_bar:
            return True

        print('Missing a foo or a bar to make a foobar')
        return False

    def make(self, available_items=None, serial_number=0, current_money=0):
        print('Robot is trying to make foobar')
        if not available_items:
            available_items = []

        has_found_foo = False
        has_found_bar = False
        bar           = None
        foo           = None

        for item in available_items:
            if has_found_bar and has_found_foo:
                break
            if item.name == 'bar':
                bar = item
                has_found_bar = True
            elif item.name == 'foo':
                foo = item
                has_found_foo = True

        available_items.remove(foo)
        available_items.remove(bar)

        success_probability      = 0.6
        list_of_candidates       = [True, False]
        probability_distribution = [success_probability, 1 - success_probability]
        # 60% chances of making the foobar, else we keep the bar and drop the foo.
        result                   = choice(list_of_candidates, 1, p=probability_distribution)
        sleeper(AvailableProduct.FOOBAR)

        is_foobar_success = list(result)[0]
        if is_foobar_success:
            print('Robot made a new foobar')
            foobar = Foobar(serial_number)
            foobar.serial_number = f'{foobar.serial_number}' \
                                   f'_foo{foo.serial_number}_bar{bar.serial_number}'
            return foobar
        else:
            print('Robot failed to make a new foobar. Keeps the bar and loses the foo.')
            return bar


class SaleMaker(ProductionMaker):
    """
        Used to sale some foobars and make money.
    """
    def check_possible(self, available_items=None, current_money=0):
        if not available_items:
            available_items = []
        for item in available_items:
            if item.name == 'foobar':
                return True
        print('Impossible to make a sale without foobar.')
        return False

    def make(self, available_items=None, serial_number=0, current_money=0):
        print('Robot is selling foobars')
        if not available_items:
            available_items = []
        dealer_result = DealerResult()
        foobar_list   = [item for item in available_items if item.name == 'foobar']
        foobar_nb     = len(foobar_list)
        new_money     = min(foobar_nb, MAX_FOOBAR_SALE)
        dealer_result.money = new_money
        dealer_result.items_to_remove = foobar_list[:new_money]
        sleeper(AvailableProduct.SALE)
        print('Robot sold some foobars')
        return dealer_result


class BuyMaker(ProductionMaker):
    """
        Used to buy some new robots
    """
    def check_possible(self, available_items=None, current_money=0):
        if not available_items:
            available_items = []
        foo_list = [item for item in available_items if item.name == 'foo']
        if len(foo_list) >= NB_FOO_BUY and current_money >= COST_ROBOT:
            return True
        print(f'Impossible! Missing some stuff to buy some new robots. '
              f'One robot cost {COST_ROBOT} plus {NB_FOO_BUY} foos')
        return False

    def make(self, available_items=None, serial_number=0, current_money=0):
        print('Robot is buying other robots.')
        if not available_items:
            available_items = []
        dealer_result    = DealerResult()
        foo_list         = [item for item in available_items if item.name == 'foo']
        nb_foos          = len(foo_list)
        nb_robots_bought = int(min(current_money/COST_ROBOT, nb_foos/NB_FOO_BUY))

        dealer_result.items_to_remove   = foo_list[:nb_robots_bought * NB_FOO_BUY]
        dealer_result.money             = nb_robots_bought * COST_ROBOT
        dealer_result.new_robots_number = nb_robots_bought
        sleeper(AvailableProduct.SALE)
        print(f'Robot bought {nb_robots_bought} other robot(s)')
        return dealer_result


class ProductMachine:
    """
        Deal with each activity
    """
    factories   = []
    initialized = False
    state       = None  # previous activity

    def __init__(self):
        if not self.initialized:
            self.initialized = True
            for d in AvailableProduct:
                name           = d.name[0] + d.name[1:].lower()
                maker_name     = name + 'Maker'
                maker_instance = eval(maker_name)()
                self.factories.append((name, maker_instance))

    def plan_activity(self):
        print('Available activities:')
        for i, f in enumerate(self.factories):
            print(f'{i} - {f[0]}')

        idx = user_input(self.factories)
        self.change_activity(idx)
        return idx

    def change_activity(self, idx):
        # Checking if changing of activity
        if not self.state:
            self.state = idx
        elif self.state and self.state != idx:
            print('Robot is changing activity')
            time.sleep(5 / CONFIG_GAME_SPEED)
            print('Robot changed activity')
            self.state = idx

    def make_activity(self, next_serial_number, available_items=None, current_money=0):
        if not available_items:
            available_items = []

        idx          = self.plan_activity()
        new_activity = self.factories[idx][1]
        is_possible  = new_activity.check_possible(available_items, current_money)
        if is_possible:
            return new_activity.make(available_items, next_serial_number, current_money)
        return None


class Production(ABC):
    """
        Base class to make any kind of production
    """
    def __init__(self, machine, max_robots):
        self.machine               = machine
        self.max_robots            = max_robots
        self.current_robots_number = 0
        self.available_items       = []
        self.next_serial_number    = 1
        self.money                 = 0

    def start(self): pass
    def take_turn(self): pass
    def deal_with_result(self, result): pass

    @property
    def finished_production(self): pass

    @property
    def items_summary(self):
        d = defaultdict(int)
        for item in self.available_items:
            d[item.name] += 1

        result = ''
        i = 0
        for el, nb in d.items():
            result += str(nb) + ' ' + el
            i += 1
            result += '' if i == len(d) else ' - '

        return 'no item' if not d else result

    def run(self):
        self.start()
        while not self.finished_production:
            self.take_turn()
        print(f'Hey man, finally {self.max_robots} robots!')


class ProductProduction(Production):
    """
        Class to make a foobar production - this is our game.
    """
    def __init__(self, machine):
        super().__init__(machine, max_robots=MAX_ROBOTS_END_GAME)
        self.current_robots_number = NB_ROBOTS_START_GAME

    @property
    def finished_production(self):
        return self.current_robots_number == self.max_robots

    def start(self):
        print(f'Starting a production of foobars with {self.current_robots_number} robots.')

    def deal_with_result(self, result):
        if isinstance(result, Product):
            self.available_items.append(result)
            self.next_serial_number += 1
        elif isinstance(result, DealerResult):
            if result.new_robots_number:
                self.current_robots_number += result.new_robots_number
                self.money                 -= result.money
            elif result.money:
                self.money += result.money

            for item_to_remove in result.items_to_remove:
                self.available_items.remove(item_to_remove)

    def log_details(self):
        if CONFIG_LOG_DETAILS and self.available_items:
            print(f'\nAvailable Items details:')
            for item in self.available_items:
                print(item)
            print('\n')

    def take_turn(self):
        print(f'Currently {self.current_robots_number} robots and {self.money}€ available. '
              f'You also have: {self.items_summary}')
        result = self.machine.make_activity(self.next_serial_number, self.available_items, self.money)
        self.deal_with_result(result)
        self.log_details()


if __name__ == '__main__':
    product_machine = ProductMachine()
    product_prod    = ProductProduction(product_machine)
    product_prod.run()
