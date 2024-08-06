<?php
$jsonFilePath = 'posts.json';

$rawData = file_get_contents('php://input');
$data = json_decode($rawData, true);

if ($data === null || !isset($data['id'])) {
    echo json_encode(["status" => "error", "message" => "Invalid JSON input"]);
    exit();
}

$idToRemove = $data['id'];

$existingData = [];
if (file_exists($jsonFilePath)) {
    $existingData = json_decode(file_get_contents($jsonFilePath), true);
    if ($existingData === null) {
        $existingData = [];
    }
}

$newData = array_map(function($post) use ($idToRemove) {
    if ($post['id'] === $idToRemove) {
        $post['deleted'] = true; // Mark as deleted instead of removing
    }
    return $post;
}, $existingData);

file_put_contents($jsonFilePath, json_encode(array_values($newData), JSON_PRETTY_PRINT));

echo json_encode(["status" => "success"]);
?>
