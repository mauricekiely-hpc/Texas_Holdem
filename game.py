import random
import json
import sys
from itertools import permutations
from collections import Counter

class Card():
    def __init__(self, symbol: str, suit: str, value: int):
        self.symbol = symbol
        self.value = value
        self.suit = suit
        self.display = f"{symbol}{suit} "

class Deck():
    def __init__(self):
        self.cards = []

        vals = {
            '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
            'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14,
        }

        suits = {
            'Hearts':'♡', 'Diamonds':'♢', 'Clubs':'♣', 'Spades':'♠'
        }

        for symbol, value in vals.items():
            for suit, suit_name in suits.items():
                card = Card(symbol, suit_name, value)
                self.cards.append(card)

class Player():
    def __init__(self):
        self.label = ''
        self.hand = []
        self.stack = 0
        self.bet = 0
        self.best_hand = []



def main():
    deck = Deck()
    random.shuffle(deck.cards)
    players, sb_index = define_players(deck)

    global pot
    pot = 0

    # Return the players remaining after the first round of betting
    players_left = betting(players, sb_index, True)
    players_left = {player:players[player] for player in players_left.copy()}

    # Settling if everyone folds
    if len(players_left) == 1:
        settle(players_left.keys()[0], players)
        sys.exit

    # Display the cards on the flop and append them to the hands of each player
    flop_cards = flop(deck, players_left.values())

    # Flop Betting and player ordering
    players_left = betting(players_left, None, False)
    players_left = {player:players[player] for player in players_left.copy()}

    # Settling if everyone folds
    if len(players_left) == 1:
        settle(players, players_left.keys()[0],)
        sys.exit

    turn_cards = turn(deck, flop_cards, players_left.values())

    # Turn Betting and player ordering
    players_left = betting(players_left, None, False)
    players_left = {player:players[player] for player in players_left.copy()}

    # Settling if everyone folds
    if len(players_left) == 1:
        settle(players, players_left.keys()[0], )
        sys.exit

    
    river(deck, turn_cards, players_left.values())

    # River Betting and player ordering
    players_left = betting(players_left, None, False)
    players_left = {player:players[player] for player in players_left.copy()}

    # Settling if everyone folds
    if len(players_left) == 1:
        settle(players, players_left.keys()[0],)
        sys.exit



    for player in players_left:
        hands = list(permutations([card for card in players[player].hand],5))
        players_left[player].best_hand = best_hand(hands)


    winning_hand = [None]
    winners = []

    for player, hand in zip(players_left, [players_left[player].best_hand for player in players_left]):
        if winning_hand[0] is None:
            winning_hand[0] = hand
            winners.append(player)
        else:
            comparison = 0
            for i in range(5):
                if hand[i] > winning_hand[0][i]:
                    winning_hand = [hand]
                    winners = [player]
                    comparison = 1
                    break
                elif hand[i] < winning_hand[0][i]:
                    comparison = -1
                    break
            if comparison == 0:
                winners.append(player)

    # Now, 'winning_hand' contains the winning hand(s), and 'winners' contains the winner(s).
    settle(players, winners)






def define_players(deck: object):
    '''
    Initialize number of players (2 -> 8).
    Assign each player 2 cards from the deck.
    Create txt files to show each player's cards.
    Assign blinds
    Initialize stack sizes
    '''

    # Check if the configuration file exists
    try:
        with open("poker_players.json", "r+") as config_file:
            config = json.load(config_file)
            config["blind_num"] += 1
            config_file.seek(0)  # Move the file pointer to the beginning
            json.dump(config, config_file, indent=4)  # Write the modified data back
            config_file.truncate()  # If the new data is shorter, remove the extra content
    except FileNotFoundError:
        blind_ticker = 1
        # If the file doesn't exist, create it with a default value
        while True:
            try:
                num_of_players = int(input("Number of Players: "))
                if 1 < num_of_players < 9:
                    print(f"{num_of_players} Players")
                    break
            except ValueError:
                pass
            print("Enter an integer value between 2 and 8")
        config = {"num_players": num_of_players,
                  "blind_num":blind_ticker}
        with open("poker_players.json", "w") as config_file:
            json.dump(config, config_file)

    num_of_players = config["num_players"]
    blind_ticker = config["blind_num"]
            

    # Dictionary for initializing the players
    players = {}
    for i in range(1, num_of_players + 1):
        players[f"Player_{i}"] = Player()
        players[f"Player_{i}"].label = f"Player_{i}"

    # Dealing of cards
    for _ in range(2):
        for player in players.values():
            player.hand.append(deck.cards.pop(0))

    # Write Cards to txt files for readability
    for player_label, player in players.items():
        cards = []
        for card in player.hand:
            cards.append(card.display)
        
        with open(f"{player_label}.txt", 'w') as file:
            file.writelines(card for card in cards)

    # Assigning blinds
    global small_blind 
    small_blind = 10
    blind_ticker = (blind_ticker % num_of_players) if blind_ticker > num_of_players else blind_ticker
    blind_ticker = num_of_players if blind_ticker == 0 else blind_ticker

    # Create stacks 
    try:
        with open("stacks.json", "r") as stack_file:
            stacks = json.load(stack_file)

    except FileNotFoundError:
        stacks = {f"Player_{i}":1000 for i in range(1,num_of_players + 1)}
        with open("stacks.json", "w") as stack_file:
            json.dump(stacks, stack_file)

    # Apply stacks to Player objects
    for player, stack in stacks.items():
        players[player].stack = stack

    
    return players, (blind_ticker - 1)

def betting(players: dict, first_to_act_index: int, preflop: bool):
    global pot

    # Initialise players in action
    live_players = [player for player in players.keys()]
    if first_to_act_index is not None:
        live_players = live_players[first_to_act_index:] + live_players[:first_to_act_index]

    # To re-order once betting round has completed
    order_of_position = live_players

    # First round of betting for both pre and post-flop
    if preflop:
        players_left, index = betting_round([players[player] for player in live_players], preflop= True)
    else:
        players_left, index = betting_round([players[player] for player in live_players], preflop= False)

    live_players = [player.label for player in players_left]

    while not all(players[player].bet == players[live_players[0]].bet for player in live_players):
        players_left, index = betting_round([players[player] for player in live_players], False, index= index)
        live_players = [player.label for player in players_left]


    for player in order_of_position:
        if player in live_players:
            players_left = live_players[live_players.index(player):] + live_players[:live_players.index(player)]
            break

    for player in players.values():
        player.bet = 0

    return players_left
              
            

def betting_round(players, first_round = True, index = None, preflop = False):
    global pot
    if not preflop and not first_round and index is not None:
            raiser = players[index]
            players = players[index+1:] + players[:index]

    elif preflop and first_round:
        players[0].bet = small_blind
        players[1].bet = small_blind * 2 

        players[0].stack -= small_blind
        players[1].stack -= small_blind * 2 

        print(f'{players[0].label} - SB: ${small_blind} \n{players[1].label} - BB: ${small_blind * 2} ')
        players = players[2:] + players[:2]
        pot += (3 * small_blind)

    for player in players.copy():
        print("")
        to_call = max([player.bet for player in players]) - player.bet if first_round else raiser.bet - player.bet
        while True:
            try:
                action = input(f'{player.label} to act: ${to_call} to call: ')
                if not action.isnumeric():
                    action.strip().lower()

                    if action == 'f' or action == 'fold':
                        fold(players, player, to_call)
                        break

                    if action == 'c' or action == 'call':                
                        call(player, to_call)
                        break

                    if action == 'a' or action == 'all' or action == 'all in':
                        ...

                    if action == 'exit':
                        sys.exit()

                else:
                    action = int(action)

                if action == to_call:
                    call(player, to_call)
                    break

                if to_call <  action <= player.stack:
                    raise_to(player, to_call, action)
                    if not first_round:
                        players.append(raiser)
                    return players, players.index(player)
                
            except:
                print('Please Enter Valid action! ')
    if not first_round:
                        players.append(raiser)
    return players, index


def fold(players ,player, to_call):
    global pot
    if to_call == 0:
        call(player, to_call)

    else:
        print(f'{player.label} folds.')
        players.remove(player)
    

def call(player, to_call):
    global pot
    if to_call == 0:
        print(f'{player.label} checks')
    else:
        print(f'{player.label} call ${to_call}')
        player.bet += to_call
        pot += to_call
        player.stack -= to_call


def raise_to(player, to_call, action):
    global pot
    print(f'{player.label} raised to ${action}')
    pot += action
    player.bet += action
    player.stack -= action


def flop(deck: list, players):
    print("\nFlop: \n------------")
    deck.cards.pop(0)
    flop_cards = []
    for _ in range(3):
        card = deck.cards.pop(0)
        print(card.display, end=" ")
        flop_cards.append(card)
        for player in players:
            player.hand.append(card)
    print("\n------------\n")
    return flop_cards


def turn(deck: list, flop_cards: list, players):
    print("\nTurn: \n---------------")
    deck.cards.pop(0)
    card = deck.cards.pop(0)
    flop_cards.append(card)
    for player in players:
        player.hand.append(card)
    for card in flop_cards:
        print(card.display, end=" ")
    print("\n---------------\n")
    return flop_cards

        
def river(deck: list, flop_cards: list, players):
    print("\nRiver: \n-------------------")
    deck.cards.pop(0)
    card = deck.cards.pop(0)
    flop_cards.append(card)
    for player in players:
        player.hand.append(card)
    for card in flop_cards:
        print(card.display, end=" ")
    print("\n-------------------\n")

def straight_flush(hand):
    return straight(hand) and flush(hand)

def four_of_a_kind(hand):
    value_count = Counter(card.value for card in hand)
    return max(count == 4 for count in value_count.values())

def full_house(hand):
    value_count = Counter(card.value for card in hand)
    return (max(count == 3 for count in value_count.values()) and sum(count == 2 for count in value_count.values()) == 1) 

def flush(hand):
    suits = [card.suit for card in hand]
    suit_counts = Counter(suits)
    return any(count == 5 for count in suit_counts.values())

def straight(hand):
    values = sorted(set(card.value for card in hand))
    if len(values) == 5 and values[0] - values[-1] == 4:
        return True
    
    # Check for 5 high straigt
    if set(values) == {2, 3, 4, 5, 14}:
        return True
    
    return False

def three_of_a_kind(hand):
    value_count = Counter(card.value for card in hand)
    return (max(count == 3 for count in value_count.values()) and sum(count == 2 for count in value_count.values()) == 0) 

def two_pair(hand):
    value_count = Counter(card.value for card in hand)
    return (max(count == 2 for count in value_count.values()) and sum(count == 2 for count in value_count.values()) == 2) 

def pair(hand):
    value_count = Counter(card.value for card in hand)
    return (max(count == 2 for count in value_count.values()) and sum(count == 1 for count in value_count.values()) == 3) 

def rank_hand(hand):
    ranked_hand =[]
    if straight_flush(hand):
        ranked_hand.append(9)
        sorted_hand = (sorted([card.value for card in hand],reverse=True))

    elif four_of_a_kind(hand):
        ranked_hand.append(8)
        x = [card.value for card in hand]
        sorted_hand = sorted(x, key=lambda y: (-x.count(y), -y))

    elif full_house(hand):
        ranked_hand.append(7)
        x = [card.value for card in hand]
        sorted_hand = sorted(x, key=lambda y: (-x.count(y), -y))

    elif flush(hand):
        ranked_hand.append(6)
        sorted_hand = (sorted([card.value for card in hand],reverse=True))

    elif straight(hand):
        ranked_hand.append(5)
        if 14 in [card.value for card in hand]:
            ranked_hand.append([14,2,3,4,5])
            sorted_hand = (sorted([card.value for card in hand],reverse=True))

    elif three_of_a_kind(hand):
        ranked_hand.append(4)
        x = [card.value for card in hand]
        sorted_hand = sorted(x, key=lambda y: (-x.count(y), -y))

    elif two_pair(hand):
        ranked_hand.append(3)
        x = [card.value for card in hand]
        sorted_hand = sorted(x, key=lambda y: (-x.count(y), -y))
    
    elif pair(hand):
        ranked_hand.append(2)
        x = [card.value for card in hand]
        sorted_hand = sorted(x, key=lambda y: (-x.count(y), -y))

    
    else:
        ranked_hand.append(1)
        sorted_hand = sorted([card.value for card in hand],reverse=True)

    ranked_hand += sorted_hand
    return ranked_hand

       
def best_hand(hands:list):
    best_hand = None
    for hand in hands:
        hand = rank_hand(list(hand))
        
        if best_hand is None:
            best_hand = hand
        else:
            for i in range(5):
                if hand[i] > best_hand[i]:
                    best_hand = hand
                    break
                elif hand[i] < best_hand[i]:
                    break
    return best_hand


def settle(players, winner):
    global pot
    if len(winner) != 1:
        print(f'\nSplit Pot: {pot}')
        pot = pot/len(winner)
        for player in winner:
            players[player].stack += pot

    else:
        winner = winner[0]
        print(f'\n{winner} wins :${pot} ')
        players[winner].stack += pot
    pot = 0

    sorted_players = dict(sorted(players.items(), key=lambda item: item[0]))
    stacks = {player:players[player].stack for player in sorted_players}

    with open("stacks.json", "w") as stack_file:
            json.dump(stacks, stack_file)




if __name__ == "__main__":
    main()  