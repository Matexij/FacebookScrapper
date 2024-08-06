<?php
$taskFilePath = 'tasks.json';
$postsFilePath = 'posts.json';

$rawData = file_get_contents('php://input');
$data = json_decode($rawData, true);

if ($data === null || !isset($data['id'])) {
    echo json_encode(["status" => "error", "message" => "Invalid JSON input"]);
    exit();
}

$idToProcess = $data['id'];

$tasks = [];
if (file_exists($taskFilePath)) {
    $tasks = json_decode(file_get_contents($taskFilePath), true);
    if ($tasks === null) {
        $tasks = [];
    }
}

$posts = [];
if (file_exists($postsFilePath)) {
    $posts = json_decode(file_get_contents($postsFilePath), true);
    if ($posts === null) {
        $posts = [];
    }
}

// Mark the post as deleted
foreach ($posts as &$post) {
    if ($post['id'] === $idToProcess) {
        $post['deleted'] = true;
        break;
    }
}
file_put_contents($postsFilePath, json_encode($posts, JSON_PRETTY_PRINT));

$task = [
    'id' => $idToProcess,
    'processed' => false
];
$tasks[] = $task;

file_put_contents($taskFilePath, json_encode($tasks, JSON_PRETTY_PRINT));

echo json_encode(["status" => "success"]);
?>