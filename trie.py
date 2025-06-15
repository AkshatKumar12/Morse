# trie.py

import re

class TrieNode:
    """A node in the Trie data structure."""
    def __init__(self):
        self.children = {}
        self.is_end_of_word = False

class Trie:
    """
    Trie data structure for prefix-based searching and text recommendations.
    """
    def __init__(self):
        self.root = TrieNode()

    def _clean_word(self, word):
        """
        Internal method to normalize a word by making it lowercase and
        removing punctuation.
        """
        # Remove any character that is not a word character or whitespace
        return re.sub(r'[^\w]', '', word).lower()

    def insert(self, word):
        """Inserts a word into the Trie."""
        cleaned_word = self._clean_word(word)
        if not cleaned_word:
            return
        
        node = self.root
        for char in cleaned_word:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.is_end_of_word = True

    def search_prefix(self, prefix):
        """
        Returns a list of all words in the Trie that start with the given prefix.
        """
        cleaned_prefix = self._clean_word(prefix)
        if not cleaned_prefix:
            return []
            
        node = self.root
        try:
            for char in cleaned_prefix:
                node = node.children[char]
        except KeyError:
            return [] # Prefix not found

        # 'node' is now at the end of the prefix. Find all words from this point.
        return self._find_words_from_node(node, cleaned_prefix)

    def _find_words_from_node(self, node, current_prefix):
        """
        A recursive helper function to find all words from a given node.
        """
        words = []
        if node.is_end_of_word:
            words.append(current_prefix)

        for char, child_node in node.children.items():
            words.extend(self._find_words_from_node(child_node, current_prefix + char))
        
        return words