const JOKES = [
  'Why did the broom arrive late? It over-swept!',
  'What did one plate say to the other? Dinner is on me!',
  'Why was the math book tired? It had too many problems!',
  'What kind of tree fits in your hand? A palm tree!',
  'Why did the cookie visit the doctor? It felt crummy!',
  'What do clouds wear under their shorts? Thunderwear!',
  'Why can’t bicycles keep secrets? They are always two-tired!',
  'What did the ocean say to the beach? Nothing—it just waved!',
  'Why did the teddy bear skip dessert? It was stuffed!',
  'What has ears but cannot hear? A cornfield!',
  'Why did the banana use sunscreen? It did not want to peel!',
  'What do you call cheese that is not yours? Nacho cheese!',
  'Why did the student eat homework? The teacher said it was easy as pie!',
  'What is a robot’s favorite snack? Computer chips!',
  'Why are frogs so happy? They eat whatever bugs them!',
  'What did the zero say to the eight? Nice belt!',
  'Why did the scarecrow win an award? It was outstanding in its field!',
  'What do you call a sleeping dinosaur? A dino-snore!',
  'Why was the broom proud? It swept the competition!',
  'What is a cat’s favorite color? Purrr-ple!',
]

export function jokeForDate(date: string) {
  const index = [...date].reduce((total, character) => total + character.charCodeAt(0), 0)
  return JOKES[index % JOKES.length]
}
