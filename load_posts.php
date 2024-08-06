<?php

require 'vendor/autoload.php'; // Make sure to load the composer autoload

use GuzzleHttp\Client;
use WebSocket\Client as WebSocketClient;

$postsFilePath = 'posts.json';

// Load posts
$posts = [];
if (file_exists($postsFilePath)) {
    $posts = json_decode(file_get_contents($postsFilePath), true);
    if ($posts === null) {
        $posts = [];
    }
}

// Filter posts to exclude those marked as deleted
$filteredPosts = array_filter($posts, function($post) {
    return !isset($post['deleted']) || $post['deleted'] === false;
});

print(gettype($filteredPosts));
if (!empty($filteredPosts)) {
    error_log("New posts to send: " . print_r($filteredPosts, true));
    $wsData = json_encode($filteredPosts);
    try {
        $wsClient = new WebSocketClient("ws://localhost:8080");
        $wsClient->send($wsData);
        $wsClient->close();
    } catch (Exception $e) {
        error_log("WebSocket error: " . $e->getMessage());
    }
}

http_response_code(200);
?>
