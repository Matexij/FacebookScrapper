<?php
// your-script.php

require 'vendor/autoload.php'; // Make sure to load the composer autoload

use GuzzleHttp\Client;
use WebSocket\Client as WebSocketClient;

$jsonFilePath = 'posts.json';

$rawData = file_get_contents('php://input');
$data = json_decode($rawData, true);

if ($data === null) {
    error_log("Invalid JSON input");
    http_response_code(400);
    echo json_encode(["error" => "Invalid JSON"]);
    exit();
}

//error_log("Received data: " . print_r($data, true));

$existingData = [];
if (file_exists($jsonFilePath)) {
    $existingData = json_decode(file_get_contents($jsonFilePath), true);
    if ($existingData === null) {
        $existingData = [];
    }
}

error_log("Existing data: " . print_r($existingData, true));

function postExists($post, $existingData) {
    foreach ($existingData as $existingPost) {
        if ($existingPost['text'] === $post['text']) {
            return true;
        }
    }
    return false;
}

$newPosts = [];
foreach ($data as $post) {
    if (!postExists($post, $existingData)) {
        $post['id'] = uniqid(); // Generate a unique ID for the post
        $post['deleted'] = false;
        $newPosts[] = $post;
        $existingData[] = $post;
    }
}
file_put_contents($jsonFilePath, json_encode($existingData, JSON_PRETTY_PRINT));

if (!empty($newPosts)) {
    error_log("New posts to send: " . print_r($newPosts, true));
    $wsData = json_encode($newPosts);
    try {
        $wsClient = new WebSocketClient("ws://localhost:8080");
        $wsClient->send($wsData);
        $wsClient->close();
        error_log('sent');
    } catch (Exception $e) {
        error_log("WebSocket error: " . $e->getMessage());
    }
}else{
    error_log('empty array');
}
http_response_code(200);
echo json_encode(["status" => "success"]);
?>