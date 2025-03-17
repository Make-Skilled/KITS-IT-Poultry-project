// SPDX-License-Identifier: MIT
pragma solidity >=0.4.22 <0.9.0;

contract poultry {
    struct User {
        string fullname;
        string email;
        string password;
        bool exists;
    }

    mapping(string => User) private users; // email -> User

    constructor() public {
    }

    function addUser(string memory _fullname, string memory _email, string memory _password) public returns (bool) {
        // Check if user already exists
        if(users[_email].exists) {
            return false;
        }

        // Add new user
        users[_email] = User({
            fullname: _fullname,
            email: _email,
            password: _password,
            exists: true
        });

        return true;
    }

    function getUserByEmail(string memory _email) public view returns (string memory, string memory, string memory, bool) {
        User memory user = users[_email];
        return (user.fullname, user.email, user.password, user.exists);
    }

    function userLogin(string memory _email, string memory _password) public view returns (bool) {
        // Check if user exists and password matches
        if(users[_email].exists && 
           keccak256(abi.encodePacked(users[_email].password)) == keccak256(abi.encodePacked(_password))) {
            return true;
        }
        return false;
    }
}
