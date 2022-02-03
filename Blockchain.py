
import hashlib
import json
from time import time
from urllib.parse import urlparse
from uuid import uuid4
import requests
from flask import Flask, jsonify, request

class Blockchain(object):
    def __init__(self):
        self.chain = []
        self.currentTransactions = []
        self.newBlock(previousHash=1, proof=100)
        self.nodes = set()
    def newBlock(self, proof, previousHash=None):
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.currentTransactions,
            'proof': proof,
            'previousHash': previousHash or self.hash(self.chain[-1])
        }
        self.currentTransactions = []
        self.chain.append(block)
        return block
    def newTransaction(self, sender, recipient, amount):
        self.currentTransactions.append({
            'sender': sender,
            'recipients': recipient,
            'amount': amount
        })
        return self.lastBlock['index'] + 1
    @property
    def lastBlock(self):
        return self.chain[-1]
    @staticmethod
    def hash(block):
        blockString =  json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(blockString).hexdigest()
    def proofOfWork(self, lastProof):
        proof = 0
        while self.validProof(lastProof, proof) is False:
            proof += 1 
        return proof
    @staticmethod
    def validProof(lastProof, proof):
        guess = f'{lastProof}{proof}'.encode()
        hash = hashlib.sha256(guess).hexdigest()
        return hash[:7] == '5964823'
    def registerNode(self, address):
        parserURL = urlparse(address)
        self.nodes.add(parserURL.netloc)
    def validChain(self, chain):
        lastBlock = chain[0]
        currentIndex = 1
        while currentIndex < len(chain):
            block = chain[currentIndex]
            print(f'{lastBlock}')
            print(f'{block}')
            print("\n-----------\n")
            if block['previousHash'] != self.hash(lastBlock):
                return False
            if not self.validProof(lastBlock['proof'], block['proof']):
                return False
            lastBlock = block
            currentIndex += 1
        return True
    def resolveConflicts(self):
        neighbours = self.nodes
        newChain = None

        maxLength = len(self.chain)

        for node in neighbours:
            print(node)
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']
                if length > maxLength and self.validChain(chain):
                    maxLength = length
                    newChain = chain

        if newChain:
            self.chain = newChain
            return True

        return False


app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

nodeIdentifier = str(uuid4()).replace('-','')

blockchain = Blockchain()

@app.route('/mine', methods=['GET'])
def mine():
    lastBlock = blockchain.lastBlock
    lastProof = blockchain.lastBlock['proof']
    proof = blockchain.proofOfWork(lastProof)
    blockchain.newTransaction(sender='0', recipient=nodeIdentifier, amount=1)
    previousHash = blockchain.hash(lastBlock)
    block = blockchain.newBlock(proof, previousHash)

    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previousHash'],
    }
    return jsonify(response), 200

@app.route('/transactions/new', methods=['POST'])
def newTransaction():
    values = request.get_json()
    print(values)
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400
    index = blockchain.newTransaction(values['sender'], values['recipient'], values['amount'])

    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response), 201

@app.route('/chain', methods=['GET'])
def fullChain():
    response = {
        'chain':blockchain.chain,
        'length':len(blockchain.chain)
    }
    return jsonify(response), 200
@app.route('/nodes/register', methods=['POST'])
def registerNodes():
    values = request.get_json(force=True)

    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.registerNode(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201
@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolveConflicts()
    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }
    return jsonify(response), 200    
    
if __name__ == '__main__':
    port=input('name port: ')
    app.run(host='0.0.0.0', port=port)