"""
Utilities for 'monKey cards', card-style stat sheets for Appditto's MonKeys
    Copyright (C) 2021  Vyryn

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import math

# Simply switch this if you want to use a different nano fork, though other services this depends on will likely break
address_prefix = "ban_"
# The image header packing
img_headers = {"format": "png", "size": "400", "background": False}
img_headers_packed = "?format=png&size=400&background=False"
# The api to request monkey stats from
monkey_api = "https://monkey.banano.cc/api/v1/monkey/dtl/"
# The api to request monkey images from
image_api = "https://monkey.banano.cc/api/v1/monkey/"
# The possible types of accessories
accessory_names = [
    "glasses",
    "hat",
    "misc",
    "shirt_pants",
    "shoes",
    "tail_accessory",
    "mouth",
]
# Each accessory category's odds of appearing on a given monkey (from https://github.com/appditto/MonKey)
accessory_odds = {
    "glasses": 0.25,
    "hat": 0.35,
    "misc": 0.3,
    "shirt_pants": 0.25,
    "shoes": 0.22,
    "tail_accessory": 0.2,
    "mouth": 1,
}
# The combined weights of each accessory category (from https://github.com/appditto/MonKey)
total_weights = {
    "glasses": 8,
    "hat": 19.4,
    "misc": 11.29,
    "shirt_pants": 6,
    "mouth": 5.56,
    "shoes": 6,
    "tail_accessory": 1,
}

sf = 2  # A factor that makes somewhat rarer items more rare. Any value other than 1 makes rarities fake,
# but more intuitively lines up with our perception of rarity, leading to a more fun feel.
"""All the accessories. Done for performance reasons. File name: (nice_name, abs_rarity, pg)"""
# Stats from https://github.com/appditto/MonKey

accessories_list = {
    "eye-patch-[w-0.5].svg": (
        "Eye Patch",
        0.5**sf / total_weights["glasses"] * accessory_odds["glasses"],
        True,
    ),
    "glasses-nerd-cyan-[w-1].svg": (
        "Cyan Nerd Glasses",
        1 / total_weights["glasses"] * accessory_odds["glasses"],
        True,
    ),
    "glasses-nerd-green-[w-1].svg": (
        "Green Nerd Glasses",
        1 / total_weights["glasses"] * accessory_odds["glasses"],
        True,
    ),
    "glasses-nerd-pink-[w-1].svg": (
        "Pink Nerd Glasses",
        1 / total_weights["glasses"] * accessory_odds["glasses"],
        True,
    ),
    "monocle-[w-0.5].svg": (
        "Monacle",
        0.5**sf * total_weights["glasses"] * accessory_odds["glasses"],
        True,
    ),
    "sunglasses-aviator-cyan-[removes-eyes][w-1].svg": (
        "Cyan Aviator Glasses",
        1 / total_weights["glasses"] * accessory_odds["glasses"],
        True,
    ),
    "sunglasses-aviator-green-[removes-eyes][w-1].svg": (
        "Green Aviator Glasses",
        1 / total_weights["glasses"] * accessory_odds["glasses"],
        True,
    ),
    "sunglasses-aviator-yellow-[removes-eyes][w-1].svg": (
        "Yellow Aviator Glasses",
        1 / total_weights["glasses"] * accessory_odds["glasses"],
        True,
    ),
    "sunglasses-thug-[removes-eyes][w-1].svg": (
        "Thug Sunglasses",
        1 / total_weights["glasses"] * accessory_odds["glasses"],
        True,
    ),
    "bandana-[w-1].svg": (
        "Bandana",
        1 / total_weights["hat"] * accessory_odds["hat"],
        True,
    ),
    "beanie-[w-1].svg": (
        "Beanie",
        1 / total_weights["hat"] * accessory_odds["hat"],
        True,
    ),
    "beanie-banano-[w-1].svg": (
        "Banano Beanie",
        1 / total_weights["hat"] * accessory_odds["hat"],
        True,
    ),
    "beanie-hippie-[unique][w-0.125].svg": (
        "Hippie Beanie",
        0.125**sf / total_weights["hat"] * accessory_odds["hat"],
        False,
    ),
    "beanie-long-[colorable-random][w-1].svg": (
        "Long Beanie",
        1 / total_weights["hat"] * accessory_odds["hat"],
        True,
    ),
    "beanie-long-banano-[colorable-random][w-1].svg": (
        "Long Banano Beanie",
        1 / total_weights["hat"] * accessory_odds["hat"],
        True,
    ),
    "cap-[w-0.8].svg": (
        "Cap",
        0.8**sf / total_weights["hat"] * accessory_odds["hat"],
        True,
    ),
    "cap-backwards-[w-1].svg": (
        "Backwards Cap",
        1 / total_weights["hat"] * accessory_odds["hat"],
        True,
    ),
    "cap-banano-[w-0.8].svg": (
        "Banano Cap",
        0.8**sf / total_weights["hat"] * accessory_odds["hat"],
        True,
    ),
    "cap-bebe-[w-0.8].svg": (
        "Bebe Cap",
        0.8**sf / total_weights["hat"] * accessory_odds["hat"],
        True,
    ),
    "cap-carlos-[w-0.8].svg": (
        "Carlos Cap",
        0.8**sf / total_weights["hat"] * accessory_odds["hat"],
        True,
    ),
    "cap-hng-[w-0.8].svg": (
        "Hng Cap",
        0.8**sf / total_weights["hat"] * accessory_odds["hat"],
        True,
    ),
    "cap-hng-plus-[unique][w-0.125].svg": (
        "Very Hng Cap",
        0.125**sf / total_weights["hat"] * accessory_odds["hat"],
        True,
    ),
    "cap-kappa-[w-0.8].svg": (
        "Kappa Cap",
        0.8**sf / total_weights["hat"] * accessory_odds["hat"],
        True,
    ),
    "cap-pepe-[w-0.8].svg": (
        "Pepe Cap",
        0.8**sf / total_weights["hat"] * accessory_odds["hat"],
        False,
    ),
    "cap-rick-[w-0.8].svg": (
        "Rick Cap",
        0.8**sf / total_weights["hat"] * accessory_odds["hat"],
        True,
    ),
    "cap-smug-[w-0.8].svg": (
        "Smug Cap",
        0.8**sf / total_weights["hat"] * accessory_odds["hat"],
        True,
    ),
    "cap-smug-green-[w-0.8].svg": (
        "Green Smug Cap",
        0.8**sf / total_weights["hat"] * accessory_odds["hat"],
        True,
    ),
    "cap-thonk-[w-0.8].svg": (
        "Thonk Cap",
        0.8**sf / total_weights["hat"] * accessory_odds["hat"],
        True,
    ),
    "crown-[unique][w-0.225].svg": (
        "Crown",
        0.225**sf / total_weights["hat"] * accessory_odds["hat"],
        True,
    ),
    "fedora-[w-1].svg": (
        "Fedora",
        1 / total_weights["hat"] * accessory_odds["hat"],
        True,
    ),
    "fedora-long-[w-1].svg": (
        "Long Fedora",
        1 / total_weights["hat"] * accessory_odds["hat"],
        True,
    ),
    "hat-cowboy-[w-1].svg": (
        "Cowby Hat",
        1 / total_weights["hat"] * accessory_odds["hat"],
        True,
    ),
    "hat-jester-[unique][w-0.125].svg": (
        "Jester Hat",
        0.125**sf / total_weights["hat"] * accessory_odds["hat"],
        True,
    ),
    "helmet-viking-[w-1].svg": (
        "Viking Hat",
        1 / total_weights["hat"] * accessory_odds["hat"],
        True,
    ),
    "banana-hands-[above-hands][removes-hands][w-1].svg": (
        "Two Bananas",
        1 / total_weights["misc"] * accessory_odds["misc"],
        True,
    ),
    "banana-right-hand-[above-hands][removes-hand-right][w-1].svg": (
        "One Banana",
        1 / total_weights["misc"] * accessory_odds["misc"],
        True,
    ),
    "bowtie-[above-hands][w-1].svg": (
        "Bowtie",
        1 / total_weights["misc"] * accessory_odds["misc"],
        True,
    ),
    "camera-[above-shirts-pants][w-1].svg": (
        "Camera",
        1 / total_weights["misc"] * accessory_odds["misc"],
        True,
    ),
    "club-[above-hands][removes-hands][w-1].svg": (
        "Club",
        1 / total_weights["misc"] * accessory_odds["misc"],
        True,
    ),
    "flamethrower-[removes-hands][above-hands][w-0.04].svg": (
        "Flamethrower",
        0.04**sf / total_weights["misc"] * accessory_odds["misc"],
        True,
    ),
    "gloves-white-[above-hands][removes-hands][w-1].svg": (
        "White Gloves",
        1 / total_weights["misc"] * accessory_odds["misc"],
        True,
    ),
    "guitar-[above-hands][removes-left-hand][w-1].svg": (
        "Guitar",
        1 / total_weights["misc"] * accessory_odds["misc"],
        True,
    ),
    "microphone-[above-hands][removes-hand-right][w-1].svg": (
        "Microphone",
        1 / total_weights["misc"] * accessory_odds["misc"],
        True,
    ),
    "necklace-boss-[above-shirts-pants][w-0.75].svg": (
        "Boss Necklace",
        0.75**sf / total_weights["misc"] * accessory_odds["misc"],
        False,
    ),
    "tie-cyan-[above-shirts-pants][w-1].svg": (
        "Cyan Tie",
        1 / total_weights["misc"] * accessory_odds["misc"],
        True,
    ),
    "tie-pink-[above-shirts-pants][w-1].svg": (
        "Pink Tie",
        1 / total_weights["misc"] * accessory_odds["misc"],
        True,
    ),
    "whisky-right-[above-hands][removes-hand-right][w-0.5].svg": (
        "Whiskey Bottle",
        0.5**sf / total_weights["misc"] * accessory_odds["misc"],
        False,
    ),
    "cigar-[w-0.5].svg": (
        "Cigar",
        0.5**sf / total_weights["mouth"] * accessory_odds["mouth"],
        False,
    ),
    "confused-[w-1].svg": (
        "Confused Face",
        1 / total_weights["mouth"] * accessory_odds["mouth"],
        True,
    ),
    "joint-[unique][w-0.06].svg": (
        "Joint",
        0.06**sf / total_weights["mouth"] * accessory_odds["mouth"],
        False,
    ),
    "meh-[w-1].svg": (
        "Meh Face",
        1 / total_weights["mouth"] * accessory_odds["mouth"],
        True,
    ),
    "pipe-[w-0.5].svg": (
        "Pipe",
        0.5**sf / total_weights["mouth"] * accessory_odds["mouth"],
        False,
    ),
    "smile-big-teeth-[w-1].svg": (
        "Toothy Grin",
        1 / total_weights["mouth"] * accessory_odds["mouth"],
        True,
    ),
    "smile-normal-[w-1].svg": (
        "Smile",
        1 / total_weights["mouth"] * accessory_odds["mouth"],
        True,
    ),
    "smile-tongue-[w-0.5].svg": (
        "Teasing Face",
        0.5**sf / total_weights["mouth"] * accessory_odds["mouth"],
        True,
    ),
    "overalls-blue[w-1].svg": (
        "Blue Overalls",
        1 / total_weights["shirt_pants"] * accessory_odds["shirt_pants"],
        True,
    ),
    "overalls-red[w-1].svg": (
        "Red Overalls",
        1 / total_weights["shirt_pants"] * accessory_odds["shirt_pants"],
        True,
    ),
    "pants-business-blue-[removes-legs][w-1].svg": (
        "Business Pants",
        1 / total_weights["shirt_pants"] * accessory_odds["shirt_pants"],
        True,
    ),
    "pants-flower-[removes-legs][w-1].svg": (
        "Flowery Pants",
        1 / total_weights["shirt_pants"] * accessory_odds["shirt_pants"],
        True,
    ),
    "tshirt-long-stripes-[colorable-random][w-1].svg": (
        "Striped Shirt",
        1 / total_weights["shirt_pants"] * accessory_odds["shirt_pants"],
        True,
    ),
    "tshirt-short-white[w-1].svg": (
        "White Shirt",
        1 / total_weights["shirt_pants"] * accessory_odds["shirt_pants"],
        True,
    ),
    "sneakers-blue-[removes-feet][w-1].svg": (
        "Blue Sneakers",
        1 / total_weights["shoes"] * accessory_odds["shoes"],
        True,
    ),
    "sneakers-green-[removes-feet][w-1].svg": (
        "Green Sneakers",
        1 / total_weights["shoes"] * accessory_odds["shoes"],
        True,
    ),
    "sneakers-red-[removes-feet][w-1].svg": (
        "Red Sneakers",
        1 / total_weights["shoes"] * accessory_odds["shoes"],
        True,
    ),
    "sneakers-swagger-[removes-feet][w-1].svg": (
        "Swaggy Sneakers",
        1 / total_weights["shoes"] * accessory_odds["shoes"],
        True,
    ),
    "socks-h-stripe-[removes-feet][w-1].svg": (
        "Zebra Socks",
        1 / total_weights["shoes"] * accessory_odds["shoes"],
        True,
    ),
    "socks-v-stripe-[colorable-random][removes-feet][w-1].svg": (
        "Crazy Socks",
        1 / total_weights["shoes"] * accessory_odds["shoes"],
        True,
    ),
    "tail-sock-[colorable-random][w-1].svg": (
        "Tail Warmer",
        1 / total_weights["tail_accessory"] * accessory_odds["tail_accessory"],
        True,
    ),
}

pg_lookup = dict(map(lambda x: (x[0], x[2]), accessories_list.values()))
# The possible types of monKey accessories
types_of_accessories = [
    "glasses",
    "hat",
    "misc",
    "mouth",
    "shirt_and_pants",
    "shoes",
    "tail",
]
# What to show as the api result for a vanity monkey (vanity monkeys don't return a proper api result)
vanity_status = "Lame Fake Monkey"
boilerplate_monkey_api_response = {
    "accessories": {
        "glasses": [],
        "hat": [],
        "misc": [],
        "mouth": [],
        "shirt_and_pants": [],
        "shoes": [],
        "tail": [],
    },
    "address": "",
    "status": vanity_status,
}


class Card:
    allowed_attrs = {
        "name": "Monkey",
        "address": "None",
        "seed": "Unknown",
        "key": None,
        "glasses": None,
        "hat": None,
        "misc": None,
        "mouth": None,
        "shirt_pants": None,
        "shoes": None,
        "tail_accessory": None,
        "r_glasses": 1,
        "r_hat": 1,
        "r_misc": 1,
        "r_mouth": 1,
        "r_shirt_pants": 1,
        "r_shoes": 1,
        "r_tail_accessory": 1,
        "rarest_rarity": None,
        "rarest_item": None,
        "img": None,
    }
    unprinted_attrs = [
        "name",
        "seed",
        "abs_rarity",
        "rarest_rarity",
        "r_glasses",
        "r_hat",
        "r_misc",
        "r_mouth",
        "r_shirt_pants",
        "r_shoes",
        "r_tail_accessory",
        "accessories",
    ]

    def __init__(self, **kwargs):
        self.address = None
        self.seed = None
        self.name = "Monkey"
        self.accessories = []
        for key, default in self.allowed_attrs.items():
            if key in kwargs:
                setattr(self, key, kwargs[key])
                if key in accessory_odds:
                    self.accessories.append(kwargs[key])
            elif default is not None:
                setattr(self, key, default)
        if self.name == self.allowed_attrs["name"] and self.address is not None:
            if len(self.address) > 12:  # type:ignore[unreachable]
                # definitely is reachable
                self.name = self.address[5:12]
            elif len(self.address) > 5:
                self.name = self.address[5:]
            else:
                self.name = self.address
        # Establish rarity value as a fraction
        self.abs_rarity = 1
        for category in accessory_odds:
            self.abs_rarity *= self.__dict__[f"r_{category}"]
        # Based on true fractional rarity value, convert to an unbounded decimal most commonly 1 but varying
        # to 10 or higher, each successive rarity 8 times more rare.
        self.rarity = math.log(1 / self.abs_rarity, 8) - 4
        if self.rarity < 1:
            self.rarity = 1
        # Show rarity as a number of stars from 1-10
        self.stars = ("★" * int(self.rarity)) + ("☆" * (10 - int(self.rarity)))
        if self.rarity > 10:
            # For extremely rare star values, 'double up' stars
            self.stars = (int(self.rarity - 10)) * "⍟" + ("★" * (20 - int(self.rarity)))

    def __str__(self):
        string = f"MonKey **{self.name}**:\n"
        for attr, val in self.__dict__.items():
            pretty_attr = attr.replace("_", " ").title()
            if attr not in self.unprinted_attrs:
                if isinstance(val, float):
                    string += f"\t**{pretty_attr}**: `{val:.2f}`\n"
                elif attr == "stars":
                    string += f"{val}\n"
                else:
                    string += f"\t**{pretty_attr}**: `{val}`\n"
        return string

    def is_pg(self, accessories=None):
        if accessories is None:
            accessories = self.accessories
        for accessory in accessories:
            if not pg_lookup[accessory]:
                return False
        return True

    def string(self):
        return self.__dict__.items()
