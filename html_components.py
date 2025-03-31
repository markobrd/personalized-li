html_top = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LinkedIn-like Page</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f3f2ef;
            margin: 0;
            padding: 0;
        }
        .container {
            max-width: 600px;
            margin: 20px auto;
            padding: 10px;
        }
        .card {
            background-color: #fff;
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 15px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .profile {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 8px;
        }
        .profile img {
            width: 40px;
            height: 40px;
            border-radius: 50%;
        }
        .profile h2 {
            font-size: 18px;
            margin: 0;
        }
        .profile p {
            color: gray;
            font-size: 14px;
            margin: 0;
        }
        .post-content {
            margin: 10px 0;
        }
        .actions {
            display: flex;
            gap: 20px;
        }
        .actions button {
            background: none;
            border: none;
            color: gray;
            cursor: pointer;
        }
        .actions button:hover {
            color: #0073b1;
        }
    </style>
</head>
<body>
    <div class="container">"""


html_bottom = """</div>
</body>
</html>"""