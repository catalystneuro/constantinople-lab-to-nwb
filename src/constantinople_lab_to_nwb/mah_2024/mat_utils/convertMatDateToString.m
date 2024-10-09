% Utility script to load all .mat files from a specified folder path, convert
% the 'date' field from datetime format to string format for compatibility
% with Python, and overwrite the original files in place with the modified data.

% Define the folder path
folderPath = '/Volumes/T9/Constantinople/A_Structs';  % Adjust this path as needed

% Get a list of all .mat files in the specified folder
matFiles = dir(fullfile(folderPath, '*.mat'));

% Iterate over each .mat file
for i = 1:length(matFiles)
    % Construct the full file path
    filePath = fullfile(matFiles(i).folder, matFiles(i).name);

    % Load the .mat file
    load(filePath);

    % Check if 'date' field exists and is of type datetime
    if isfield(A, 'date') && isa(A.date, 'datetime')
        % Convert the datetime column to a string format (e.g., 'dd-mmm-yyyy')
        A.date = datestr(A.date, 'dd-mmm-yyyy');

        % Save the modified data back to the file
        save(filePath, 'A');
    else
        error('The "date" field does not exist or is not of type datetime.');
    end

    clear A;
end

