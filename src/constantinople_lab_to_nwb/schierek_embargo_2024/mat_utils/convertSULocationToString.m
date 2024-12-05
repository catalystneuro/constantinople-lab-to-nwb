% MATLAB script to process all .mat files in a specified directory,
% checking for 'SU' structure and converting 'location' to a plain string if it exists

% Specify the path to your directory containing the .mat files
folderPath = '/Volumes/T9/Constantinople/Ephys Data/'; % Replace with your actual folder path

% Get a list of all .mat files in the directory
files = dir(fullfile(folderPath, '**', '*.mat'));
matFiles = fullfile({files.folder}, {files.name});

% Loop through each .mat file in the directory
for k = 1:length(matFiles)
    matFilePath = fullfile(folderPath, matFiles(k));
    matFilePath = char(matFiles{k});  % Ensure it is a character array
    % Load the .mat file
    try
        data = load(matFilePath);
    catch ME
        % Handle the error
        disp(['An error occurred: ', ME.message]);
        continue
    end

    % Check if 'SU' structure exists in the loaded data
    if isfield(data, 'SU')
        SU = data.SU;  % Get the SU structure
        numUnits = length(SU);

        % Iterate over each unit in the SU structure
        for i = 1:numUnits
            if isfield(SU{i}, 'location')
                % Check and convert location if it is a cell array
                if iscell(SU{i}.location) && ~isempty(SU{i}.location)
                    locationStr = SU{i}.location{1}; % Extract first element if it is a cell
                else
                    locationStr = SU{i}.location;
                end
                SU{i}.location = locationStr;
            end
        end

        S = data.S;
        save(matFilePath, 'S', 'SU');
        disp(['Processed and saved: ', matFilePath]);
            % Clear variables to free up workspace
        clear SU;
        clear S;
        clear data;
    end
end
