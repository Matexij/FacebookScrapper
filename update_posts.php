<?php
// Define the path to the JSON file
$json_file_path = 'posts_data.json';

// Get the raw POST data
$input = file_get_contents('php://input');

// Decode the JSON data
$data = json_decode($input, true);

// Check if data was received and is valid
if (isset($data['posts']) && is_array($data['posts'])) {
    // Check if the JSON file exists
    if (file_exists($json_file_path)) {
        // Read the existing data from the file
        $existing_data = file_get_contents($json_file_path);
        $posts = json_decode($existing_data, true);
        
        // Check if the existing data is an array
        if (!is_array($posts)) {
            $posts = [];
        }
    } else {
        // Initialize an empty array if file does not exist
        $posts = [];
    }
    
    // Append the new posts to the existing data
    $posts = array_merge($posts, $data['posts']);
    
    // Save the updated data back to the JSON file
    $json_data = json_encode($posts, JSON_PRETTY_PRINT);
    if (file_put_contents($json_file_path, $json_data)) {
        // Send a success response
        echo json_encode(['status' => 'success']);
    } else {
        // Send an error response
        echo json_encode(['status' => 'error', 'message' => 'Failed to save data']);
    }
} else {
    // Send an error response if no valid data was received
    echo json_encode(['status' => 'error', 'message' => 'Invalid data received']);
}
?>
