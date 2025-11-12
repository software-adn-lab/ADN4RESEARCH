from nltk import pos_tag, word_tokenize
from nltk.chunk import RegexpParser
sentence = """What are the best practices for software development?"""
tokens = word_tokenize(sentence)

tagged = pos_tag(tokens)
# Definimos un patrón para capturar sustantivos compuestos (NN NN)
gramatica = r"""
  NP: {<NN.*><NN.*>}   # Dos sustantivos seguidos
"""
parser = RegexpParser(gramatica)
arbol = parser.parse(tagged)
for subtree in arbol.subtrees():
    if subtree.label() == 'NP':
        frase = " ".join(palabra for palabra, etiqueta in subtree)
        print(f"Frase compuesta detectada: {frase}")

print(tagged[0:10])